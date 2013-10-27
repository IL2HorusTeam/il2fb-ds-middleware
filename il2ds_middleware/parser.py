# -*- coding: utf-8 -*-

import re

from twisted.python import log

from zope.interface import implementer

import il2ds_log_parser.parser as lp
import il2ds_log_parser.regex as lpre
from il2ds_middleware.constants import MISSION_STATUS, PILOT_LEAVE_REASON
from il2ds_middleware.interface.parser import *
from il2ds_middleware.regex import *


@implementer(IConsoleParser)
class ConsolePassthroughParser(object):

    def passthrough(self, data):
        return data

    parse_line = server_info  = mission_load = mission_destroy = \
    mission_begin = mission_end = mission_status = passthrough


@implementer(IConsoleParser)
class ConsoleParser(object):

    _buffer = None

    def __init__(self, services):
        self.pilot_service, self.mission_service = services

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
            self.pilot_service.user_joined(info)
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


@implementer(ILineParser)
class EventLogPassthroughParser(object):

    def parse_line(self, data):
        return data


@implementer(ILineParser)
class EventLogParser(lp.MultipleParser):

    def __init__(self, services):
        pilots, objects, missions = services
        parsers = [
            # User state events
            (
                lp.TimeStampedRegexParser(lpre.RX_WENT_TO_MENU),
                pilots.went_to_menu
            ),
            (   lp.PositionedRegexParser(lpre.RX_SELECTED_ARMY),
                pilots.selected_army
            ),
            # Crew member events
            (lp.SeatRegexParser(lpre.RX_SEAT_OCCUPIED), pilots.seat_occupied),
            (lp.SeatRegexParser(lpre.RX_KILLED), pilots.was_killed),
            (
                lp.SeatVictimOfUserRegexParser(lpre.RX_KILLED_BY_USER),
                pilots.was_killed_by_user
            ),
            (lp.SeatRegexParser(lpre.RX_BAILED_OUT), pilots.bailed_out),
            (
                lp.SeatRegexParser(lpre.RX_PARACHUTE_OPENED),
                pilots.parachute_opened
            ),
            (lp.SeatRegexParser(lpre.RX_CAPTURED), pilots.was_captured),
            (lp.SeatRegexParser(lpre.RX_WOUNDED), pilots.was_wounded),
            (
                lp.SeatRegexParser(lpre.RX_HEAVILY_WOUNDED),
                pilots.was_heavily_wounded
            ),
            # Destruction events
            (
                lp.PositionedRegexParser(lpre.RX_DESTROYED_BLD),
                objects.building_destroyed_by_user
            ),
            (
                lp.PositionedRegexParser(lpre.RX_DESTROYED_TREE),
                objects.tree_destroyed_by_user
            ),
            (
                lp.PositionedRegexParser(lpre.RX_DESTROYED_STATIC),
                objects.static_destroyed_by_user
            ),
            (
                lp.PositionedRegexParser(lpre.RX_DESTROYED_BRIDGE),
                objects.bridge_destroyed_by_user
            ),
            # Events of lightning effects
            (
                lp.PositionedRegexParser(lpre.RX_TOGGLE_LANDING_LIGHTS),
                pilots.toggle_landing_lights
            ),
            (
                lp.PositionedRegexParser(lpre.RX_TOGGLE_WINGTIP_SMOKES),
                pilots.toggle_wingtip_smokes
            ),
            # Aircraft events
            (
                lp.FuelRegexParser(lpre.RX_WEAPONS_LOADED),
                pilots.weapons_loaded
            ),
            (lp.PositionedRegexParser(lpre.RX_TOOK_OFF), pilots.took_off),
            (lp.PositionedRegexParser(lpre.RX_CRASHED), pilots.crashed),
            (lp.PositionedRegexParser(lpre.RX_LANDED), pilots.landed),
            (
                lp.PositionedRegexParser(lpre.RX_DAMAGED_SELF),
                pilots.damaged_self
            ),
            (
                lp.VictimOfUserRegexParser(lpre.RX_DAMAGED_BY_USER),
                pilots.was_damaged_by_user
            ),
            (
                lp.PositionedRegexParser(lpre.RX_DAMAGED_ON_GROUND),
                pilots.was_damaged_on_ground
            ),
            (
                lp.PositionedRegexParser(lpre.RX_SHOT_DOWN_SELF),
                pilots.shot_down_self
            ),
            (
                lp.VictimOfUserRegexParser(lpre.RX_SHOT_DOWN_BY_USER),
                pilots.was_shot_down_by_user
            ),
            (
                lp.VictimOfStaticRegexParser(lpre.RX_SHOT_DOWN_BY_STATIC),
                pilots.was_shot_down_by_static
            ),
            # Mission flow events
            (
                lp.DateTimeStampedRegexParser(lpre.RX_MISSION_WON),
                missions.was_won
            ),
            (lp.NumeratedRegexParser(lpre.RX_TARGET_END), missions.target_end),
        ]
        super(EventLogParser, self).__init__(parsers=parsers)

    def parse_line(self, line):
        return self(line)


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
