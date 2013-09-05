# -*- coding: utf-8 -*-

import re

from twisted.python import log

from zope.interface import implementer

from il2ds_middleware.constants import MISSION_STATUS, PILOT_LEAVE_REASON
from il2ds_middleware.interface.parser import (IDeviceLinkParser,
    IEventLogParser, IConsoleParser, )
from il2ds_middleware.regex import *


@implementer(IConsoleParser)
class ConsoleParser(object):

    _buffer = None

    def __init__(self, pilot_service):
        self.pilot_service = pilot_service

    def parse_line(self, line):
        if self.user_joined(line):
            return
        elif self.user_left(line):
            return

    def server_info(self, lines):
        result = {}
        for line in lines:
            key, value = line.split(':')
            result[key.strip().lower()] = value.strip()
        return result

    def mission_status(self, lines):
        for line in lines:
            if line == "Mission NOT loaded":
                return (MISSION_STATUS.NOT_LOADED, None, )
            elif line.endswith("is Loaded"):
                return (MISSION_STATUS.LOADED, line.split()[1], )
            elif line.endswith("is Playing"):
                return (MISSION_STATUS.PLAYING, line.split()[1], )
        return lines

    mission_load = mission_destroy = mission_status
    mission_begin = mission_end = mission_status

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


@implementer(IEventLogParser)
class EventLogParser(object):

    def __init__(self, (pilot_service, objects_service)):
        ps = pilot_service
        obs = objects_service
        self.parsers = (
            (RX_SEAT_OCCUPIED, self.seat_occupied, ps.seat_occupied),
            (RX_WEAPONS_LOADED, self.weapons_loaded, ps.weapons_loaded),
            (RX_KILLED, self.was_killed, ps.was_killed),
            (RX_SHOT_DOWN, self.was_shot_down, ps.was_shot_down),
            (RX_SELECTED_ARMY, self.selected_army, ps.selected_army),
            (RX_WENT_TO_MENU, self.went_to_menu, ps.went_to_menu),
            (RX_DESTROYED, self.was_destroyed, obs.was_destroyed),
        )

    def parse_line(self, line):
        for rx, parser, dst in self.parsers:
            m = re.match(rx, line)
            if m:
                dst(parser(m.groups()))
                return

    def seat_occupied(self, groups):
        return {
            'callsign': groups[0],
            'aircraft': groups[1],
            'seat': int(groups[2]),
            'pos': self._get_pos((groups[3], groups[4])),
        }

    def weapons_loaded(self, groups):
        return {
            'callsign': groups[0],
            'aircraft': groups[1],
            'weapons': groups[2],
            'fuel': int(groups[3]),
        }

    def was_killed(self, groups):
        return {
            'callsign': groups[0],
            'aircraft': groups[1],
            'seat': int(groups[2]),
            'pos': self._get_pos((groups[3], groups[4])),
        }

    def was_shot_down(self, groups):
        return {
            'victim': {
                'callsign': groups[0],
                'aircraft': groups[1],
            },
            'attacker': {
                'callsign': groups[2],
                'aircraft': groups[3],
            },
            'pos': self._get_pos((groups[4], groups[5])),
        }

    def selected_army(self, groups):
        return {
            'callsign': groups[0],
            'army': groups[1],
            'pos': self._get_pos((groups[2], groups[3])),
        }

    def went_to_menu(self, groups):
        return {
            'callsign': groups[0],
        }

    def was_destroyed(self, groups):
        return {
            'victim': groups[0],
            'attacker': groups[1],
            'pos': self._get_pos((groups[2], groups[3])),
        }

    def _get_pos(self, (x, y)):
        return {
            'x': float(x),
            'y': float(y),
        }


@implementer(IDeviceLinkParser)
class DeviceLinkParser(object):

    def pilot_count(self, data):
        return int(data)

    def pilot_pos(self, data):
        return self._parse_pos(data, 'callsign')

    def all_pilots_pos(self, datas):
        return map(self.pilot_pos, datas)

    static_count = pilot_count

    def static_pos(self, data):
        return self._parse_pos(data)

    def all_static_pos(self, datas):
        return map(self.static_pos, datas)

    def _parse_pos(self, data, name_attr='name'):
        idx, info = data.split(':')
        attr, x, y, z = info.split(';')
        return {
            'idx': int(idx),
            name_attr: attr,
            'pos': {
                'x': int(x),
                'y': int(y),
                'z': int(z),
            },
        }
