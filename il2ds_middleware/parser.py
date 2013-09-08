# -*- coding: utf-8 -*-

import re

from twisted.python import log

from zope.interface import implementer

from il2ds_middleware.constants import MISSION_STATUS, PILOT_LEAVE_REASON
from il2ds_middleware.interface.parser import (IDeviceLinkParser,
    IEventLogParser, IConsoleParser, )
from il2ds_middleware.regex import *


@implementer(IConsoleParser)
class ConsolePassthroughParser(object):

    def passthrough(self, data):
        return data

    parse_line = server_info = mission_status = passthrough
    mission_load = mission_destroy = mission_status
    mission_begin = mission_end = mission_status


@implementer(IConsoleParser)
class ConsoleParser(object):

    _buffer = None

    def __init__(self, (pilot_service, mission_service)):
        self.pilot_service = pilot_service
        self.mission_service = mission_service

    def parse_line(self, line):
        while True:
            if self.user_chat(line):
                break
            if self.user_joined(line):
                break
            if self.user_left(line):
                break
            if self._mission_status(line):
                break
            return False
        return True

    def server_info(self, lines):
        result = {}
        for line in lines:
            key, value = line.split(':')
            result[key.strip().lower()] = value.strip()
        return result

    def mission_status(self, lines):
        for line in lines:
            info = self._mission_status(line)
            if info:
                return info
        return lines

    def _mission_status(self, line):
        info = None
        if line == "Mission NOT loaded":
            info = (MISSION_STATUS.NOT_LOADED, None, )
        elif line.endswith("is Loaded"):
            info = (MISSION_STATUS.LOADED, line.split()[1], )
        elif line.endswith("is Playing"):
            info = (MISSION_STATUS.PLAYING, line.split()[1], )
        if info:
            self.mission_service.on_status_info(info)
        return info

    def user_joined(self, line):
        m = re.match(RX_USER_JOIN, line)
        if not m:
            return False
        else:
            groups = m.groups()
            info = {
                'channel': int(groups[0]),
                'ip': groups[1],
                'callsign': groups[2],
            }
            self.pilot_service.user_join(info)
            return True

    def user_left(self, line):
        m = re.match(RX_USER_LEFT, line)
        if m:
            groups = m.groups()
            reason = (PILOT_LEAVE_REASON.KICKED if 'kicked' in groups[2]
                else PILOT_LEAVE_REASON.DISCONNECTED)
            self._buffer = {
                'ip': groups[0],
                'channel': int(groups[1]),
                'reason': reason,
            }
            return True
        if line.endswith("has left the game.") and self._buffer:
            info, self._buffer = self._buffer, None
            info['callsign'] = line.split()[2]
            self.pilot_service.user_left(info)
            return True
        return False

    def user_chat(self, line):
        m = re.match(RX_USER_CHAT, line)
        if not m:
            return False
        else:
            callsign, msg = m.groups()
            if callsign != "Server":
                info = (callsign, msg.decode('unicode-escape'))
                self.pilot_service.user_chat(info)
            return True


@implementer(IEventLogParser)
class EventLogPassthroughParser(object):

    def passthrough(self, data):
        return data

    parse_line = seat_occupied = weapons_loaded = was_killed = \
    was_shot_down = selected_army = went_to_menu = was_destroyed = \
    in_flight = landed = damaged = damaged_on_ground = \
    turned_wingtip_smokes = crashed = bailed_out = was_captured = \
    was_captured = was_wounded = was_heavily_wounded = removed = passthrough


@implementer(IEventLogParser)
class EventLogParser(object):

    def __init__(self, (pilot_service, objects_service)):
        ps = pilot_service
        obs = objects_service
        self.parsers = (
            (RX_SEAT_OCCUPIED, self.seat_occupied, ps.seat_occupied),
            (RX_SELECTED_ARMY, self.selected_army, ps.selected_army),
            (RX_DESTROYED, self.was_destroyed, obs.was_destroyed),
            (RX_WEAPONS_LOADED, self.weapons_loaded, ps.weapons_loaded),
            (RX_KILLED, self.was_killed, ps.was_killed),
            (RX_SHOT_DOWN, self.was_shot_down, ps.was_shot_down),
            (RX_WENT_TO_MENU, self.went_to_menu, ps.went_to_menu),
            (RX_IN_FLIGHT, self.in_flight, ps.in_flight),
            (RX_LANDED, self.landed, ps.landed),
            (RX_CRASHED, self.crashed, ps.crashed),
            (RX_DAMAGED, self.damaged, ps.damaged),
            (RX_DAMAGED_ON_GROUND, self.damaged_on_ground,
                ps.damaged_on_ground),
            (RX_TURNED_WINGTIP_SMOKES, self.turned_wingtip_smokes,
                ps.turned_wingtip_smokes),
            (RX_BAILED_OUT, self.bailed_out, ps.bailed_out),
            (RX_WAS_CAPTURED, self.was_captured, ps.was_captured),
            (RX_WAS_WOUNDED, self.was_wounded, ps.was_wounded),
            (RX_WAS_HEAVILY_WOUNDED, self.was_heavily_wounded,
                ps.was_heavily_wounded),
            (RX_REMOVED, self.removed, ps.removed),
        )

    def parse_line(self, line):
        for rx, parser, dst in self.parsers:
            m = re.match(rx, line)
            if m:
                dst(parser(m.groups()))
                return True
        return False

    def _seat_event(self, groups):
        return {
            'callsign': groups[0],
            'aircraft': groups[1],
            'seat': int(groups[2]),
            'pos': self._pos((groups[3], groups[4])),
        }

    def _aircraft_event(self, groups):
        return {
            'callsign': groups[0],
            'aircraft': groups[1],
            'pos': self._pos((groups[2], groups[3])),
        }

    def _actor(self, data):
        info = data.split(':')
        is_user = len(info) == 2
        actor = {
            'is_user': is_user,
        }
        if is_user:
            actor['callsign'] = info[0]
            actor['aircraft'] = info[1]
        else:
            actor['name'] = info[0]
        return actor

    def _pos(self, (x, y)):
        return {
            'x': float(x),
            'y': float(y),
        }

    seat_occupied = was_killed = bailed_out = was_captured = was_wounded = \
    was_heavily_wounded = _seat_event

    in_flight = damaged_on_ground = crashed = removed = _aircraft_event

    def weapons_loaded(self, groups):
        return {
            'callsign': groups[0],
            'aircraft': groups[1],
            'weapons': groups[2],
            'fuel': int(groups[3]),
        }

    def was_shot_down(self, groups):
        return {
            'victim': {
                'callsign': groups[0],
                'aircraft': groups[1],
            },
            'attacker': self._actor(groups[2]),
            'pos': self._pos((groups[3], groups[4])),
        }

    def selected_army(self, groups):
        return {
            'callsign': groups[0],
            'army': groups[1],
            'pos': self._pos((groups[2], groups[3])),
        }

    def went_to_menu(self, groups):
        return {
            'callsign': groups[0],
        }

    def was_destroyed(self, groups):
        return {
            'victim': groups[0],
            'attacker': groups[1],
            'pos': self._pos((groups[2], groups[3])),
        }

    def landed(self, groups):
        info = self._actor(groups[0])
        info.update({
            'pos': self._pos((groups[1], groups[2])),
        })
        return info

    def damaged(self, groups):
        return {
            'victim': {
                'callsign': groups[0],
                'aircraft': groups[1],
            },
            'attacker': self._actor(groups[2]),
            'pos': self._pos((groups[3], groups[4])),
        }

    def turned_wingtip_smokes(self, groups):
        return {
            'callsign': groups[0],
            'aircraft': groups[1],
            'state': groups[2],
            'pos': self._pos((groups[3], groups[4])),
        }


@implementer(IDeviceLinkParser)
class DeviceLinkPassthroughParser(object):

    def passthrough(self, data):
        return data

    pilot_count = pilot_pos = all_pilots_pos = passthrough
    static_count = static_pos = all_static_pos = passthrough


@implementer(IDeviceLinkParser)
class DeviceLinkParser(object):

    def pilot_count(self, data):
        return int(data)

    def pilot_pos(self, data):
        return self._parse_pos(data, 'callsign', strip_idx=True)

    def all_pilots_pos(self, datas):
        return map(self.pilot_pos, datas)

    static_count = pilot_count

    def static_pos(self, data):
        return self._parse_pos(data)

    def all_static_pos(self, datas):
        return map(self.static_pos, datas)

    def _parse_pos(self, data, name_attr='name', strip_idx=False):
        idx, info = data.split(':')
        attr, x, y, z = info.split(';')
        if strip_idx:
            attr = attr[:attr.rindex("_")]
        return {
            'idx': int(idx),
            name_attr: attr,
            'pos': {
                'x': int(x),
                'y': int(y),
                'z': int(z),
            },
        }
