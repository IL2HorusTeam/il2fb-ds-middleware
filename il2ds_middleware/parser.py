# -*- coding: utf-8 -*-
import re

from zope.interface import implementer

import il2ds_log_parser.content_processor as lpcp
import il2ds_log_parser.parser as lp
import il2ds_log_parser.regex as lpre
from il2ds_middleware.constants import MISSION_STATUS, PILOT_LEAVE_REASON
from il2ds_middleware.interface.parser import (ILineParser, IConsoleParser,
    IDeviceLinkParser, )
from il2ds_middleware.regex import *


@implementer(IConsoleParser)
class ConsolePassthroughParser(object):
    """
    Fake parser of server's console output which returns back given data.
    """

    def passthrough(self, data):
        return data

    parse_line = server_info = mission_status = user_joined = user_left = \
    user_chat = users_common_info = users_statistics = passthrough


@implementer(IConsoleParser)
class ConsoleParser(object):
    """
    Default parser of server's console output which tells given services about
    parsed events.
    """

    _buffer = None

    def __init__(self, services):
        """
        Input:
        `services`      # a tuple with pilots and mission services
                        # which implements IPilotsService and IMissionsService
                        # correspondingly
        """
        self.pilot_service, self.mission_service = services

    def parse_line(self, line):
        """
        Parse string line.

        Input:
        `line`      # a string to parse.

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

        def _mission_path():
            return line.split()[1]

        info = None

        if line == "Mission NOT loaded":
            info = (MISSION_STATUS.NOT_LOADED, None, )
        elif line.endswith("is Loaded"):
            info = (MISSION_STATUS.LOADED, _mission_path(), )
        elif line.endswith("is Playing"):
            info = (MISSION_STATUS.PLAYING, _mission_path(), )

        if info:
            self.mission_service.on_status_info(info)

        return info

    def user_joined(self, line):
        """
        Parse an information about joined user.

        Input:
        `line`      # a string to parse. Example:
                    # "socket channel '0', ip 192.168.1.2:21000, user0, is complete created."

        Output:
        A dictionary with the following structure:
        {
            'channel': CHANNEL,     # number of server's channel
            'ip': "IP",             # pilot's IP address
            'callsign': "CALLSIGN", # pilot's callsign
        }
        """
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
        """
        Parse an information about user who has left. This information always
        come from server in two consecutive strings. Since we can not control
        this logic, so we need to remember in buffer a result of parsing the
        1st string and wait for the 2nd.

        Input:
        `line`      # a string to parse. Example of expected values:
                    # "socketConnection with 192.168.1.2:21000 on channel 0 lost.  Reason: "
                    # "Chat: --- user0 has left the game."

        Output:
        A dictionary with the following structure:
        {
            'channel': CHANNEL,     # number of server's channel
            'ip': "IP",             # pilot's IP address
            'callsign': "CALLSIGN", # pilot's callsign

            'reason': REASON,       # PILOT_LEAVE_REASON.DISCONNECTED or
                                    # PILOT_LEAVE_REASON.KICKED
        }
        """
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
        elif line.endswith("has left the game.") and self._buffer:
            info, self._buffer = self._buffer, None
            info['callsign'] = line.split(' ', 3)[2]
            self.pilot_service.user_left(info)
            return True
        return False

    def user_chat(self, line):
        """
        Parse a chat message. Skip if it was sent by server.

        Input:
        `line`      # a string to parse. Example:
                    # "Chat: user0: \\tSome message."

        Output:
        A tuple with the following structure:
        (
            "CALLSIGN", # pilot's callsign
            "MESSAGE"   # message body
        )
        """
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

    def users_common_info(self, lines):
        """
        Parse common information about users.

        Input:
        `lines`    # A sequence of strings which represents rows of a table
                   # with information about users. The table can be obtained by
                   # executing 'user' command in DS console. Example:
                   # [
                   #     " N      Name           Ping    Score   Army        Aircraft",
                   #     " 1     user1            3       0      (0)None             ",
                   #     " 2     user2            11      111    (1)Red      * Red 90    Il-2M_Late",
                   #     " 3     user3            22      222    (2)Blue     + 99        HurricaneMkIIb",
                   # ]

        Output:
        A dictionary with the following example structure:
        {
            'CALLSIGN1': {
                'ping': PING,
                'score': SCORE,
                'army_code': ARMY_CODE,
            },
            'CALLSIGN2': {
                'ping': PING,
                'score': SCORE,
                'army_code': ARMY_CODE,
                'aircraft': {
                    'designation': "DESIGNATION",
                    'code': "AIRCRAFT_CODE",
                },
            },
        }
        """
        result = {}

        for line in lines[1:]:
            raw_info = re.split('\s{2,}', line.strip())[1:]

            callsign = raw_info.pop(0)
            info = {}
            result[callsign] = info

            info['ping'] = int(raw_info.pop(0))
            info['score'] = int(raw_info.pop(0))
            info['army_code'] = int(re.search('\d+', raw_info.pop(0)).group())

            if raw_info:
                info['aircraft'] = {
                    'designation': raw_info.pop(0),
                    'code': raw_info.pop(0),
                }

        return result

    def users_statistics(self, lines):
        """
        Parse detailed statistics about each user.

        Input:
        `lines`    # A sequence of strings which represents rows of multiple
                   # tables with information about users' statistics. The table
                   # can be obtained by executing 'user STAT' command in DS
                   # console. Example:
                   # [
                   #     "-------------------------------------------------------",
                   #     "Name: \\t\\tuser1",
                   #     "Score: \\t\\t0",
                   #     "State: \\t\\tIn Flight",
                   #     "Enemy Aircraft Kill: \\t\\t0",
                   #     "Enemy Static Aircraft Kill: \\t\\t0",
                   #     "Enemy Tank Kill: \\t\\t0",
                   #     "Enemy Car Kill: \\t\\t0",
                   #     "Enemy Artillery Kill: \\t\\t0",
                   #     "Enemy AAA Kill: \\t\\t0",
                   #     "Enemy Wagon Kill: \\t\\t0",
                   #     "Enemy Ship Kill: \\t\\t0",
                   #     "Enemy Radio Kill: \\t\\t0",
                   #     "Friend Aircraft Kill: \\t\\t0",
                   #     "Friend Static Aircraft Kill: \\t\\t0",
                   #     "Friend Tank Kill: \\t\\t0",
                   #     "Friend Car Kill: \\t\\t0",
                   #     "Friend Artillery Kill: \\t\\t0",
                   #     "Friend AAA Kill: \\t\\t0",
                   #     "Friend Wagon Kill: \\t\\t0",
                   #     "Friend Ship Kill: \\t\\t0",
                   #     "Friend Radio Kill: \\t\\t0",
                   #     "Fire Bullets: \\t\\t0",
                   #     "Hit Bullets: \\t\\t0",
                   #     "Hit Air Bullets: \\t\\t0",
                   #     "Fire Roskets: \\t\\t0",
                   #     "Hit Roskets: \\t\\t0",
                   #     "Fire Bombs: \\t\\t0",
                   #     "Hit Bombs: \\t\\t0",
                   #     "-------------------------------------------------------",
                   # ]

        Output:
        A dictionary with the following structure:
        {
            "CALLSIGN": {
                'score': SCORE,
                'state': "STATE",
                'kills': {
                    'enemy': {
                        'aircraft': VALUE,
                        'static_aircraft': VALUE,
                        'tank': VALUE,
                        'car': VALUE,
                        'artillery': VALUE,
                        'aaa': VALUE,
                        'wagon': VALUE,
                        'ship': VALUE,
                        'radio': VALUE,
                    },
                    'friend': {
                        'aircraft': VALUE,
                        'static_aircraft': VALUE,
                        'tank': VALUE,
                        'car': VALUE,
                        'artillery': VALUE,
                        'aaa': VALUE,
                        'wagon': VALUE,
                        'ship': VALUE,
                        'radio': VALUE,
                    },
                },
                'weapons': {
                    'bullets': {
                        'fire': VALUE,
                        'hit': VALUE,
                        'hit_air': VALUE,
                    },
                    'rockets': {
                        'fire': VALUE,
                        'hit': VALUE,
                    },
                    'bombs': {
                        'fire': VALUE,
                        'hit': VALUE,
                    },
                },
            },
        }
        """
        def get_blank_info():
            """
            Prepares blank statistics info.
            """
            info = {
                'kills': {
                    'enemy': {},
                    'friend': {},
                },
                'weapons': {
                    'bullets': {},
                    'rockets': {},
                    'bombs': {},
                },
            }
            return info

        def to_key(key):
            """
            Turns strings into dictionary keys.
            """
            return key.lower().replace(' ', '_')

        result = {}

        callsign = None
        info = get_blank_info()

        for line in lines[1:]:
            if line.startswith('-'):
                result[callsign] = info
                info = get_blank_info()
                continue

            attr, value = line.replace('\\t', '').split(': ')

            if attr == "Name":
                callsign = value

            elif attr == "Score":
                info['score'] = int(value)

            elif attr == "State":
                info['state'] = value

            elif attr.endswith("Kill"):
                side, target = attr.rsplit(' ', 1)[0].split(' ', 1)
                side = to_key(side)
                target = to_key(target)
                info['kills'][side][target] = int(value)

            else:
                attr, weapon = attr.rsplit(' ', 1)
                attr = to_key(attr)
                weapon = to_key(weapon).replace('sk', 'ck')
                info['weapons'][weapon][attr] = int(value)

        return result


@implementer(ILineParser)
class EventLogPassthroughParser(object):
    """
    Fake parser of events log which returns back given data.
    """

    def parse_line(self, data):
        return data


@implementer(ILineParser)
class EventLogParser(lp.MultipleParser):
    """
    Default parser of map events which tells given services about parsed
    events.
    """

    def __init__(self, services):
        """
        Input:
        `services`      # a tuple with pilots, objects and mission services
                        # which implements IPilotsService, IObjectsService and
                        # IMissionsService correspondingly
        """
        pilots, objects, missions = services
        time_position = [
            lpcp.process_time, lpcp.process_position,
        ]
        time_togle_position = [
            lpcp.process_time, lpcp.process_toggle_value,
            lpcp.process_position,
        ]
        time_seat_position = [
            lpcp.process_time, lpcp.process_seat, lpcp.process_position,
        ]
        params = (
            # Mission flow events
            (
                lpre.RX_MISSION_WON,
                [lpcp.process_time, lpcp.process_date, lpcp.process_army, ],
                missions.was_won
            ),
            (
                lpre.RX_TARGET_RESULT,
                [   lpcp.process_time, lpcp.process_number,
                    lpcp.process_target_result,
                ],
                missions.target_end
            ),
            # User state events
            (lpre.RX_WENT_TO_MENU, lpcp.process_time, pilots.went_to_menu),
            (lpre.RX_SELECTED_ARMY, time_position, pilots.selected_army),
            # # Destruction events
            (
                lpre.RX_DESTROYED_BLD,
                time_position,
                objects.building_destroyed_by_user
            ),
            (
                lpre.RX_DESTROYED_TREE,
                time_position,
                objects.tree_destroyed_by_user
            ),
            (
                lpre.RX_DESTROYED_BRIDGE,
                time_position,
                objects.bridge_destroyed_by_user
            ),
            (
                lpre.RX_DESTROYED_STATIC,
                time_position,
                objects.static_destroyed_by_user
            ),
            # Lightning effect events
            (
                lpre.RX_TOGGLE_LANDING_LIGHTS,
                time_togle_position,
                pilots.toggle_landing_lights
            ),
            (
                lpre.RX_TOGGLE_WINGTIP_SMOKES,
                time_togle_position,
                pilots.toggle_wingtip_smokes
            ),
            # Aircraft events
            (
                lpre.RX_WEAPONS_LOADED,
                [
                    lpcp.process_time, lpcp.process_fuel,
                    lpcp.process_position,
                ],
                pilots.weapons_loaded
            ),
            (lpre.RX_TOOK_OFF, time_position, pilots.took_off),
            (lpre.RX_CRASHED, time_position, pilots.crashed),
            (lpre.RX_LANDED, time_position, pilots.landed),
            (
                lpre.RX_DAMAGED_ON_GROUND,
                time_position,
                pilots.was_damaged_on_ground
            ),
            (lpre.RX_DAMAGED_SELF, time_position, pilots.damaged_self),
            (
                lpre.RX_DAMAGED_BY_USER,
                [
                    lpcp.process_time, lpcp.process_attacking_user,
                    lpcp.process_position,
                ],
                pilots.was_damaged_by_user
            ),
            (lpre.RX_SHOT_DOWN_SELF, time_position, pilots.shot_down_self),
            (
                lpre.RX_SHOT_DOWN_BY_STATIC,
                time_position,
                pilots.was_shot_down_by_static
            ),
            (
                lpre.RX_SHOT_DOWN_BY_USER,
                [
                    lpcp.process_time, lpcp.process_attacking_user,
                    lpcp.process_position,
                ],
                pilots.was_shot_down_by_user
            ),
            # Crew member events
            (lpre.RX_SEAT_OCCUPIED, time_seat_position, pilots.seat_occupied),
            (lpre.RX_KILLED, time_seat_position, pilots.was_killed),
            (
                lpre.RX_KILLED_BY_USER,
                [
                    lpcp.process_time, lpcp.process_seat,
                    lpcp.process_attacking_user, lpcp.process_position,
                ],
                pilots.was_killed_by_user
            ),
            (lpre.RX_BAILED_OUT, time_seat_position, pilots.bailed_out),
            (
                lpre.RX_SUCCESSFULLY_BAILED_OUT,
                time_seat_position,
                pilots.parachute_opened
            ),
            (lpre.RX_WOUNDED, time_seat_position, pilots.was_wounded),
            (
                lpre.RX_HEAVILY_WOUNDED,
                time_seat_position,
                pilots.was_heavily_wounded
            ),
            (lpre.RX_CAPTURED, time_seat_position, pilots.was_captured),
        )
        parsers = [
            (lp.RegexParser(rx, processor), callback) for
                (rx, processor, callback) in params]
        super(EventLogParser, self).__init__(parsers=parsers)

    def parse_line(self, line):
        """
        Invoke __call__ method to parse string line and tell a corresponding
        service about event.

        Input:
        `line`      # a string to parse.
        """
        return self(line)


@implementer(IDeviceLinkParser)
class DeviceLinkPassthroughParser(object):
    """
    Fake parser of DeviceLink output which returns back given data.
    """

    def passthrough(self, data):
        return data

    pilot_count = pilot_pos = all_pilots_pos = passthrough
    static_count = static_pos = all_static_pos = passthrough


@implementer(IDeviceLinkParser)
class DeviceLinkParser(object):
    """
    Default parser of DeviceLink output.
    """

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
        return self._parse_pos(data, name_attr='callsign', strip_idx=True)

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
        return filter(lambda x: x is not None, map(self.pilot_pos, datas))

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
        return filter(lambda x: x is not None, map(self.static_pos, datas))

    def _parse_pos(self, data, name_attr='name', strip_idx=False):
        idx, info = data.split(':')

        if info == 'BADINDEX' or info == 'INVALID':
            return None

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
