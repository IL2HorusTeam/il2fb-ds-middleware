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

    """Fake server's console output parser which returns back given data."""

    def passthrough(self, data):
        return data

    parse_line = server_info  = mission_load = mission_destroy = \
    mission_begin = mission_end = mission_status = passthrough


@implementer(IConsoleParser)
class ConsoleParser(object):

    """
    Default server's console output parser which tells gives services about
    parsed events.
    """

    _buffer = None

    def __init__(self, services):
        """
        Input:
        `services`      # a tuple with pilots and mission services
                        # which implemente IPilotService and IMissionService
                        # correspondingly
        """
        self.pilot_service, self.mission_service = services

    def parse_line(self, line):
        """
        Parse string line.

        Input:
        `line`      # string to parse

        Output:
        `True` if string was parsed, `False` otherwise.
        """
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
        """
        Parse a sequence of strings containing information about server.

        Input:
        `lines`     # a sequence of strings containing parameter names and
                    # values separated with ':' (colon)

        Output:
        A dictionary containing parameters' values, which can be accessed by
        lower-case parameter names.
        """
        result = {}
        for line in lines:
            key, value = line.split(':')
            result[key.strip().lower()] = value.strip()
        return result

    def mission_status(self, lines):
        """
        Parse a sequence of strings containing server's output for mission
        status request.

        Input:
        `lines`     # sequence of string with information about mission status

        Output:
        A tuple (MISSION_STATUS, ["MISSION_NAME" | None]) if status was parsed
        or original sequence of strings otherwise.
        """
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
        """Parse 'user joined left' event."""
        m = re.match(RX_USER_JOIN, line, RX_FLAGS)
        if not m:
            return False
        else:
            d = m.groupdict()
            info = {
                'channel': int(d['channel']),
                'ip': d['ip'],
                'callsign': d['callsign'],
            }
            self.pilot_service.user_joined(info)
            return True

    def user_left(self, line):
        """Parse 'user has left' event."""
        m = re.match(RX_USER_LEFT, line, RX_FLAGS)
        if m:
            d = m.groupdict()
            reason = (PILOT_LEAVE_REASON.KICKED if 'kicked' in d['reason']
                else PILOT_LEAVE_REASON.DISCONNECTED)
            self._buffer = {
                'ip': d['ip'],
                'channel': int(d['channel']),
                'reason': reason,
            }
            return True
        if line.endswith("has left the game.") and self._buffer:
            info, self._buffer = self._buffer, None
            info['callsign'] = line.split(' ', 3)[2]
            self.pilot_service.user_left(info)
            return True
        return False

    def user_chat(self, line):
        """Parse 'user sent message to chat' event."""
        m = re.match(RX_USER_CHAT, line, RX_FLAGS)
        if not m:
            return False
        else:
            d = m.groupdict()
            callsign, msg = d['callsign'], d['msg']
            if callsign != "Server":
                info = (callsign, msg.decode('unicode-escape'))
                self.pilot_service.user_chat(info)
            return True


@implementer(ILineParser)
class EventLogPassthroughParser(object):

    """Fake eventss log parser which returns back given data."""

    def parse_line(self, data):
        return data


@implementer(ILineParser)
class EventLogParser(lp.MultipleParser):

    """
    Default map events parser which tells given services about parsed events.
    """

    def __init__(self, services):
        """
        Input:
        `services`      # a tuple with pilots, objects and mission services
                        # which implemente IPilotService, IObjectsService and
                        # IMissionService correspondingly
        """
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
        """
        Invoke __call__ method to parse string line and tell a corresponding
        service about event.

        Input:
        `line`      # string line to parse
        """
        return self(line)


@implementer(IDeviceLinkParser)
class DeviceLinkPassthroughParser(object):

    """Fake DeviceLink output parser which returns back given data."""

    def passthrough(self, data):
        return data

    pilot_count = pilot_pos = all_pilots_pos = passthrough
    static_count = static_pos = all_static_pos = passthrough


@implementer(IDeviceLinkParser)
class DeviceLinkParser(object):

    """Default DeviceLink output parser."""

    def pilot_count(self, data):
        """
        Convert pilots count data type to integer.

        Input:
        `data`      # string number of active pilots

        Output:
        Integer number of active pilots
        """
        return int(data)

    def pilot_pos(self, data):
        """
        Parse string presenting information about pilot's position.

        Input:
        `data`      # string in '{id};{callsign}{id}_{id};{x};{y};{z}' format
                    # where id is pilot's id number in server's DeviceLink,
                    # callsign is pilot's callsign and x, y, z - integer
                    # coordinates

        Output:
        A dictionary with the following structure:
        {
            'id': ID,               # pilot's id integer number in DeviceLink
            'callsign': "CALLSIGN", # pilot's callsign
            'pos': {                # a dictionary with position coordinates
                'x': X,             # integer x value
                'y': Y,             # integer y value
                'z': Z,             # integer z value
            },
        }
        """
        return self._parse_pos(data, 'callsign', strip_idx=True)

    def all_pilots_pos(self, datas):
        """
        Parse a sequence of strings presenting pilots' positions.

        Input:
        `datas`     # a sequence of strings in
                    # '{id};{callsign}{id}_{id};{x};{y};{z}' format where id is
                    # pilot's id number in server's DeviceLink, callsign is
                    # pilot's callsign and x, y, z - integer coordinates

        Output:
        A sequence of dictionaries with the following structure:
        {
            'id': ID,               # pilot's id integer number in DeviceLink
            'callsign': "CALLSIGN", # pilot's callsign
            'pos': {                # a dictionary with position coordinates
                'x': X,             # integer x value
                'y': Y,             # integer y value
                'z': Z,             # integer z value
            },
        }
        """
        return map(self.pilot_pos, datas)

    static_count = pilot_count

    def static_pos(self, data):
        """
        Parse string presenting information about static object's position.

        Input:
        `data`      # string in '{id};{id}_Static;{x};{y};{z}' format
                    # where id is object's id number in server's DeviceLink
                    # and x, y, z - integer coordinates

        Output:
        A dictionary with the following structure:
        {
            'id': ID,               # object's id integer number in DeviceLink
            'name': "NAME",         # object's name
            'pos': {                # a dictionary with position coordinates
                'x': X,             # integer x value
                'y': Y,             # integer y value
                'z': Z,             # integer z value
            },
        }
        """
        return self._parse_pos(data)

    def all_static_pos(self, datas):
        """
        Parse a sequence of strings presenting objects' positions.

        Input:
        `datas`     # a sequence of strings in
                    # '{id};{id}_Static;{x};{y};{z}' format
                    # where id is object's id number in server's DeviceLink
                    # and x, y, z - integer coordinates

        Output:
        A sequence of dictionaries with the following structure:
        {
            'id': ID,               # object's id integer number in DeviceLink
            'name': "NAME",         # object's name
            'pos': {                # a dictionary with position coordinates
                'x': X,             # integer x value
                'y': Y,             # integer y value
                'z': Z,             # integer z value
            },
        }
        """
        return map(self.static_pos, datas)

    def _parse_pos(self, data, name_attr='name', strip_idx=False):
        idx, info = data.split(':')
        attr, x, y, z = info.split(';')
        if strip_idx:
            attr = attr[:attr.rindex("_")]
        return {
            'id': int(idx),
            name_attr: attr,
            'pos': {
                'x': int(x),
                'y': int(y),
                'z': int(z),
            },
        }
