# -*- coding: utf-8 -*-
import tx_logging

from twisted.application.internet import TimerService
from twisted.application.service import Service

from twisted.internet import defer
from zope.interface import implementer

from il2ds_middleware.constants import MISSION_STATUS
from il2ds_middleware.interface.service import (
    IPilotsService, IObjectsService, IMissionsService, )


LOG = tx_logging.getLogger(__name__)


class ClientServiceMixin(object):
    """
    Mixin for client sevices. Console and Device Link clients must be set up
    manually.
    """

    def cl_client(self):
        """
        Get instance of server console client protocol.
        """
        raise NotImplementedError

    def dl_client(self):
        """
        Get instance of server Device Link client protocol.
        """
        raise NotImplementedError

    @staticmethod
    def radar_refresher(func):
        """
        Decorator which refreshes Device Link radar before some method is
        called.
        """
        def decorator(self, *args, **kwargs):
            if self.dl_client:
                self.dl_client.refresh_radar()
            func(self, *args, **kwargs)
        return decorator


@implementer(IPilotsService)
class MutedPilotsService(Service, ClientServiceMixin):
    """
    Base pilots muted service which does nothing.
    """

    def user_joined(self, info):
        """
        Process 'user joined server' event.

        Input:
        `info`  # A dictionary with information about user's callsign, server
                # channel number, remote IP address and port. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'channel': CHANNEL,       # channel integer number
                #     'ip': "IP",               # user's remote IP address
                # }
        """

    def user_left(self, info):
        """
        Process 'user left server' event.

        Input:
        `info`  # An object with information about user's callsign, server
                # channel number, remote IP address and port, reason of
                # disconnection. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'channel': CHANNEL,       # channel integer number
                #     'ip': "IP",               # user's remote IP address
                #     'reason': "REASON",       # reason of disconnection
                # }
        """

    def user_chat(self, info):
        """
        Process 'user sent message to chat' event.

        Input:
        `info`  # A tuple with information about user's callsign and body of
                # the message. Structure:
                # ("CALLSIGN", "MESSAGE")
        """

    def seat_occupied(self, info):
        """
        Process 'user occupied seat' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, seat number and position on map.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'seat': SEAT,     # integer number of seat
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def selected_army(self, info):
        """
        Process 'user selected army' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign, army name and position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #
                #     'time': TIME,     # time object
                #     'army': "ARMY",   # name of army
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def went_to_menu(self, info):
        """
        Process 'user went to refly menu' event.

        Input:
        `info`  # A dictionary with information about event's time, and user's
                # callsign. Structure:
                # {
                #     'time': TIME,             # time object
                #     'callsign': "CALLSIGN",   # user's callsign
                # }
        """

    def weapons_loaded(self, info):
        """
        Process 'user loaded weapons' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign, selected aircraft, its loadout and fuel percentage.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #     'loadout': "LOADOUT",     # loadout name
                #
                #     'fuel': FUEL,     # integer value of fuel percentage
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_killed(self, info):
        """
        Process 'crew member was killed' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, seat number and position on map.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'seat': SEAT,     # integer number of seat
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_killed_by_user(self, info):
        """
        Process 'crew member was killed by user' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, seat number, attacker's callsign,
                # aircraft and position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",       # user's callsign
                #     'aircraft': "AIRCRAFT",       # user's aircraft
                #     'attacker': {
                #         'callsign': "CALLSIGN",   # attacker's callsign
                #         'aircraft': "AIRCRAFT",   # attacker's aircraft
                #     },
                #
                #     'time': TIME,     # time object
                #     'seat': SEAT,     # integer number of seat
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def took_off(self, info):
        """
        Process 'user took off' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign, aircraft and position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def landed(self, info):
        """
        Process 'user landed' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign, aircraft and position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def crashed(self, info):
        """
        Process 'user crashed' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign, aircraft and position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def damaged_self(self, info):
        """
        Process 'user damaged himself' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_damaged_by_user(self, info):
        """
        Process 'user was damaged by user' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, attacker's callsign and aircraft,
                # position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",       # user's callsign
                #     'aircraft': "AIRCRAFT",       # user's aircraft
                #     'attacker': {
                #         'callsign': "CALLSIGN",   # attacker's callsign
                #         'aircraft': "AIRCRAFT",   # attacker's aircraft
                #     },
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_damaged_on_ground(self, info):
        """
        Process 'user was damaged on the ground' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def shot_down_self(self, info):
        """
        Process 'user shot down himself' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_shot_down_by_user(self, info):
        """
        Process 'user was shot down by user' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, attacker's callsign and aircraft,
                # position on map. Structure:
                # {
                #     'callsign': "CALLSIGN",       # user's callsign
                #     'aircraft': "AIRCRAFT",       # user's aircraft
                #     'attacker': {
                #         'callsign': "CALLSIGN",   # attacker's callsign
                #         'aircraft': "AIRCRAFT",   # attacker's aircraft
                #     },
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_shot_down_by_static(self, info):
        """
        Process 'user was shot down by static object' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, attacking object's name, position on
                # map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #     'attacker': "STATIC",     # attacking static's name
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def toggle_wingtip_smokes(self, info):
        """
        Process 'user toggled wingtip smokes' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign, aircraft, wingtip smokes state value and position
                # on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'value': VALUE,   # True or False
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def toggle_landing_lights(self, info):
        """
        Process 'user toggled landing lights' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign, aircraft, landing lights state value and position
                # on map. Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'value': VALUE,   # True or False
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def bailed_out(self, info):
        """
        Process 'crew member bailed out' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, seat number and position on map.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'seat': SEAT,     # integer number of seat
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def parachute_opened(self, info):
        """
        Process 'crew member's parachute opened' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, seat number and position on map.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'seat': SEAT,     # integer number of seat
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_captured(self, info):
        """
        Process 'crew member was captured' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, seat number and position on map.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'seat': SEAT,     # integer number of seat
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_wounded(self, info):
        """
        Process 'crew member was wounded' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, seat number and position on map.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'seat': SEAT,     # integer number of seat
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def was_heavily_wounded(self, info):
        """
        Process 'crew member was heavily wounded' event.

        Input:
        `info`  # A dictionary with information about event's time, user's
                # callsign and aircraft, seat number and position on map.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'seat': SEAT,     # integer number of seat
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """


@implementer(IObjectsService)
class MutedObjectsService(Service, ClientServiceMixin):
    """
    Base map objects muted service which does nothing.
    """

    def building_destroyed_by_user(self, info):
        """
        Process 'building was destroyed by user' event.

        Input:
        `info`  # A dictionary with information about event's time, building's
                # name, user's callsign and aircraft, position on map.
                # Structure:
                # {
                #     'building': "BUILDING",   # building's name
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def tree_destroyed_by_user(self, info):
        """
        Process 'tree was destroyed by user' event.

        Input:
        `info`  # A dictionary with information about event's time, tree's
                # name, user's callsign and aircraft, position on map.
                # Structure:
                # {
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'tree': "TREE",   # tree's name
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def static_destroyed_by_user(self, info):
        """
        Process 'static object was destroyed by user' event.

        Input:
        `info`  # A dictionary with information about event's time, object's
                # name, user's callsign and aircraft, position on map.
                # Structure:
                # {
                #     'static': "STATIC",       # static's name
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """

    def bridge_destroyed_by_user(self, info):
        """
        Process 'bridge was destroyed by user' event.

        Input:
        `info`  # A dictionary with information about event's time, bridge's
                # name, user's callsign and aircraft, position on map.
                # Structure:
                # {
                #     'bridge': "BRIDGE",       # bridge's name
                #     'callsign': "CALLSIGN",   # user's callsign
                #     'aircraft': "AIRCRAFT",   # user's aircraft
                #
                #     'time': TIME,     # time object
                #     'pos': {          # dictionary with position on map
                #         'x': X,       # float x value
                #         'y': Y,       # float y value
                #     },
                # }
        """


@implementer(IMissionsService)
class MutedMissionsService(Service, ClientServiceMixin):
    """
    Base mission muted service which does nothing.
    """

    def on_status_info(self, info):
        """
        Process incoming information about mission's status.

        Input:
        `info`  # A tuple containing mission's status and name. Name is `None`
                # if mission is not loaded. Structure:
                # (MISSION_STATUS, "MISSION_PATH")
        """

    def was_won(self, info):
        """
        Process 'current mission was won by an army' event.

        Input:
        `info`  # A dictionary with information about event's date, time and
                # army's name. Structure:
                # {
                #    'date': DATE,      # date object
                #    'time': TIME,      # time object
                #    'army': "ARMY",    # army name in capital letters
                # }
        """

    def target_end(self, info):
        """
        Process event of target's success or failure.

        Input:
        `info`  # A dictionary with information about target's number and
                # result. Structure:
                # {
                #    'time': TIME,          # time object
                #    'number': NUMBER,      # target's number integer value
                #    'result': "RESULT",    # "Complete" or "Failed"
                # }
        """


class MissionsService(MutedMissionsService):
    """
    Default mission service.
    """

    def __init__(self, log_watcher=None):
        """
        Input:
        `log_watcher`   # 'Service' instance used for watching mission's event
                        # log file while mission is running.
        """
        self.status = MISSION_STATUS.NOT_LOADED
        self.current_mission_path = None
        self.log_watcher = log_watcher

    def on_status_info(self, info):
        """
        Process information about mission state. See base class for more
        details.
        """
        status, current_mission_path = info
        if status != self.status:
            if status == MISSION_STATUS.PLAYING:
                self.began(info)
            elif (
                (
                    self.status == MISSION_STATUS.PLAYING
                    and status in [
                        MISSION_STATUS.LOADED, MISSION_STATUS.NOT_LOADED
                    ]
                ) or (
                    self.status in [
                        MISSION_STATUS.LOADED, MISSION_STATUS.LOADING,
                        MISSION_STATUS.STOPPING
                    ] and status == MISSION_STATUS.NOT_LOADED
                )
            ):
                self.ended(info)
        self.status, self.current_mission_path = status, current_mission_path

    def began(self, info=None):
        """
        Process 'mission has began' event.

        Input:
        `info`  # A tuple containing mission's status and name.
        """
        if self.log_watcher:
            self.log_watcher.startService()

    def ended(self, info=None):
        """
        Process 'mission has ended' event.

        Input:
        `info`  # A tuple containing mission's status and name if it is loaded
                # or status and `None` otherwise.
        """
        if self.log_watcher:
            self.log_watcher.stopService()

    def stopService(self):

        def callback(unused):
            MutedMissionsService.stopService(self)

        return self.log_watcher.stopService().addBoth(callback)


class LogWatchingService(TimerService):
    """
    Base server's events log watcher. Reads lines from specified file with
    given time period.
    """

    def __init__(self, log_path=None, period=1, parser=None):
        """
        Input:
        `log_path`      # string path to server's events log file.

        `period`        # float number of seconds to use for reading period
        """
        self.log_file = None
        self.log_path = log_path
        self.set_parser(parser)
        TimerService.__init__(self, period, self.do_watch)

    def do_watch(self):
        """
        Log reading callback.
        """
        self.log_file.seek(self.log_file.tell())
        for line in self.log_file.readlines():
            self.got_line(line)

    def set_parser(self, parser):
        self.parser = parser

    def clear_parser(self):
        self.set_parser(None)

    def got_line(self, line):
        """
        Pass line from log file to parser if it is specified.
        """
        if self.parser:
            self.parser.parse_line(line.strip())

    def startService(self):
        if self.log_file is not None or self.log_path is None:
            return
        try:
            self.log_file = open(self.log_path, 'r')
        except IOError as e:
            LOG.error("Failed to open events log: {0}.".format(e))
            self.log_file = None
        else:
            self.log_file.seek(self.log_file.tell())
            self.log_file.readlines()
            TimerService.startService(self)

    def stopService(self):
        if self.log_file is None:
            return defer.succeed(None)
        else:
            self.log_file.close()
            self.log_file = None
            return TimerService.stopService(self)
