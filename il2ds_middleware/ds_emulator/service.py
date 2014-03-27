# -*- coding: utf-8 -*-
import datetime
import tx_logging

from collections import OrderedDict

from twisted.application.service import Service, MultiService
from zope.interface import implementer

from il2ds_middleware.constants import (DEVICE_LINK_OPCODE as OPCODE,
    MISSION_STATUS, PILOT_STATE, OBJECT_STATE, )
from il2ds_middleware.interface.parser import ILineParser
from il2ds_middleware.ds_emulator.constants import LONG_OPERATION_CMD


LOG = tx_logging.getLogger(__name__)


@implementer(ILineParser)
class CommonServiceMixin():

    evt_log = None
    client = None

    def send(self, line):
        if self.client:
            self.client.message(line)
        elif self.parent:
            self.parent.send(line)


class RootService(MultiService, CommonServiceMixin):
    """
    Top-level service.
    """

    def __init__(self, log_path=None):
        MultiService.__init__(self)
        self.muted = False
        self.evt_log = EventLogger(log_path)
        self.user_command_id = 0
        self.set_server_info()
        self._init_children()

    def _init_children(self):
        """
        Initialize children services.
        """
        pilots = PilotsService()
        statics = StaticsService()
        dl = DeviceLinkService()
        missions = MissionsService()

        dl.pilots = pilots
        dl.statics = statics
        missions.device_link = dl

        for service in [pilots, statics, missions, dl, ]:
            service.setServiceParent(self)
            service.evt_log = self.evt_log

    def mute(self):
        self.muted = True

    def unmute(self):
        self.muted = False

    def startService(self):
        MultiService.startService(self)

    def stopService(self):
        self.evt_log.setServiceParent(self)
        return MultiService.stopService(self)

    def parse_line(self, line):
        if not self.muted:
            result = False
            for service in self.services:
                if not ILineParser.providedBy(service):
                    continue
                result = service.parse_line(line)
                if result:
                    break
            if not result and not self._parse(line):
                self.send("Command not found: " + line)
        return True

    def _parse(self, line):
        while True:
            if line == 'server':
                self._server_info()
                break
            if line == LONG_OPERATION_CMD:
                break
            if line.startswith("chat"):
                return self._chat(line)
            return False
        return True

    def _server_info(self):
        response = [
            "Type: Local server",
            "Name: {0}".format(self.info['name'] or "Server"),
            "Description: {0}".format(self.info['description'] or ""),
        ]
        for line in response:
            self.send(line)

    def _chat(self, line):
        idx = line.find('ALL')
        if idx < 0:
            idx = line.find('TO')
        if idx < 0:
            idx = line.find('ARMY')
        if idx < 0:
            return False
        msg = line[4:idx].strip()
        self.send("Chat: Server: \t{0}".format(msg))
        return True

    def set_server_info(self, name=None, description=None):
        self.info = {
            'name': name or "",
            'description': description or "",
        }

    def manual_input(self, line):
        self.send(line)
        self.parse_line(line)

        self.user_command_id += 1
        self.send("<consoleN><{0}>".format(self.user_command_id))


class PilotsService(Service, CommonServiceMixin):

    name = "pilots"
    channel = 1
    channel_inc = 2
    port = 21000

    def __init__(self):
        self.pilots = OrderedDict()

    def parse_line(self, line):
        while True:
            if line == "user":
                self.show_common_info()
                break
            if line == "user STAT":
                self.show_statistics()
                break
            if line.startswith("kick"):
                arg = line.split(' ', 1)[1]
                try:
                    self.kick_number(int(arg))
                except ValueError:
                    self.kick_user(arg)
                break
            return False
        return True

    def join(self, callsign, ip):

        def create_pilot():
            pilot = {
                'ip': ip,
                'channel': self.channel,
                'state': PILOT_STATE.IDLE,
                'army': "(0)None",
                'ping': 0,
                'score': 0,
                'kills': {
                    'enemy': {
                        'aircraft': 0,
                        'static_aircraft': 0,
                        'tank': 0,
                        'car': 0,
                        'artillery': 0,
                        'aaa': 0,
                        'wagon': 0,
                        'ship': 0,
                        'radio': 0,
                    },
                    'friend': {
                        'aircraft': 0,
                        'static_aircraft': 0,
                        'tank': 0,
                        'car': 0,
                        'artillery': 0,
                        'aaa': 0,
                        'wagon': 0,
                        'ship': 0,
                        'radio': 0,
                    },
                },
                'weapons': {
                    'bullets': {
                        'fire': 0,
                        'hit': 0,
                        'hit_air': 0,
                    },
                    'rockets': {
                        'fire': 0,
                        'hit': 0,
                    },
                    'bombs': {
                        'fire': 0,
                        'hit': 0,
                    },
                },
            }
            self.channel += self.channel_inc
            return pilot

        pilot = create_pilot()
        self.pilots[callsign] = pilot

        self.send("socket channel '{0}' start creating: ip {1}:{2}".format(
                  pilot['channel'], pilot['ip'], self.port))
        self.send("Chat: --- {0} joins the game.".format(callsign))
        self.send("socket channel '{0}', ip {1}:{2}, {3}, "
                  "is complete created.".format(
                  pilot['channel'], pilot['ip'], self.port, callsign))
        self.evt_log.enlog("{0} has connected".format(callsign))

    def leave(self, callsign):
        self._leave(callsign)

    def kick_number(self, number):
        try:
            callsign = self.pilots.keys()[number - 1]
        except IndexError:
            LOG.error("Kick error: invalid number {0}.".format(number))
        else:
            self.kick_user(callsign)

    def kick_user(self, callsign):
        self._leave(callsign, reason="You have been kicked from the server.")

    def _leave(self, callsign, reason=None):
        pilot = self.pilots.get(callsign)
        if pilot is None:
            LOG.error("Pilot with callsign \"{0}\" not found.".format(
                      callsign))
            return
        del self.pilots[callsign]

        line = "socketConnection with {0}:{1} on channel {2} lost.  " \
            "Reason: ".format(pilot['ip'], self.port, pilot['channel'])
        if reason:
            line += reason
        self.send(line)
        self.send("Chat: --- {0} has left the game.".format(
            callsign))
        self.evt_log.enlog("{0} has disconnected".format(callsign))

    def idle(self, callsign):
        pilot = self.pilots.get(callsign)
        if pilot is not None:
            pilot['state'] = PILOT_STATE.IDLE
            self.evt_log.enlog("{0} entered refly menu".format(callsign))

    def spawn(self, callsign, craft=None, pos=None):
        pilot = self.pilots.get(callsign)
        if pilot is not None:
            pilot['state'] = PILOT_STATE.SPAWNED
            pilot['pos'] = pos or {
                'x': 0, 'y': 0, 'z': 0, }
            pilot['craft'] = craft or {
                'code': "A6M2-21",
                'designation': "* Red 1",
                'weapons': "1xdt",
                'fuel': "100",
            }
            self.evt_log.enlog(
                "{0}:{1}(0) seat occupied by {0} at {2} {3}".format(
                callsign, pilot['craft']['code'],
                pilot['pos']['x'], pilot['pos']['y']))
            self.evt_log.enlog(
                "{0}:{1} loaded weapons '{2}' fuel {3}%".format(
                callsign, pilot['craft']['code'],
                pilot['craft']['weapons'], pilot['craft']['fuel']))

    def kill(self, callsign):
        pilot = self.pilots.get(callsign)
        if pilot is not None:
            pilot['state'] = PILOT_STATE.DEAD
            self.evt_log.enlog("{0}:{1}(0) was killed at {2} {3}".format(
                               callsign, pilot['craft']['code'],
                               pilot['pos']['x'], pilot['pos']['y']))

    def get_active(self):
        return [
            callsign for callsign in self.pilots.keys()
            if self.pilots[callsign]['state'] != PILOT_STATE.IDLE
        ]

    def show_common_info(self):
        line = " {0: <8}{1: <15}{2: <8}{3: <8}{4: <12}{5: <8}".format(
               "N", "Name", "Ping", "Score", "Army", "Aircraft")
        self.send(line)
        for i, (callsign, pilot) in enumerate(self.pilots.items()):
            craft = pilot.get('craft')
            craft_info = "{0: <12}{1}".format(
                          craft['designation'], craft['code']) if craft else ""
            line = " {0: <7}{1: <17}{2: <8}{3: <7}{4: <12}{5: <8}".format(
                   i+1, callsign, pilot['ping'], pilot['score'], pilot['army'],
                   craft_info)
            self.send(line)

    def show_statistics(self):

        def separate():
            self.send("-"*55)

        def show(name, value):
            self.send("{0}: \\t\\t{1}".format(name, value))

        separate()
        for callsign, pilot in self.pilots.iteritems():
            show("Name", callsign)
            show("Score", pilot['score'])
            show("State", pilot['state'].name)

            kills = pilot['kills']['enemy']
            show("Enemy Aircraft Kill", kills['aircraft'])
            show("Enemy Static Aircraft Kill", kills['static_aircraft'])
            show("Enemy Tank Kill", kills['tank'])
            show("Enemy Car Kill", kills['car'])
            show("Enemy Artillery Kill", kills['artillery'])
            show("Enemy AAA Kill", kills['aaa'])
            show("Enemy Wagon Kill", kills['wagon'])
            show("Enemy Ship Kill", kills['ship'])
            show("Enemy Radio Kill", kills['radio'])

            kills = pilot['kills']['friend']
            show("Friend Aircraft Kill", kills['aircraft'])
            show("Friend Static Aircraft Kill", kills['static_aircraft'])
            show("Friend Tank Kill", kills['tank'])
            show("Friend Car Kill", kills['car'])
            show("Friend Artillery Kill", kills['artillery'])
            show("Friend AAA Kill", kills['aaa'])
            show("Friend Wagon Kill", kills['wagon'])
            show("Friend Ship Kill", kills['ship'])
            show("Friend Radio Kill", kills['radio'])

            bullets = pilot['weapons']['bullets']
            show("Fire Bullets", bullets['fire'])
            show("Hit Bullets", bullets['hit'])
            show("Hit Air Bullets", bullets['hit_air'])

            rockets = pilot['weapons']['rockets']
            # Yep, yes: 'Roskets' with 's' inside.
            show("Fire Roskets", rockets['fire'])
            show("Hit Roskets", rockets['hit'])

            bombs = pilot['weapons']['bombs']
            show("Fire Bombs", bombs['fire'])
            show("Hit Bombs", bombs['hit'])

            separate()

    def stopService(self):
        self.pilots.clear()
        return Service.stopService(self)


class MissionsService(Service, CommonServiceMixin):

    name = "missions"
    status = MISSION_STATUS.NOT_LOADED
    mission = None
    device_link = None

    def parse_line(self, line):
        if not line.startswith("mission"):
            return False
        cmd = line[7:].strip()
        while True:
            if not cmd:
                self._send_status()
                break
            elif cmd.startswith("LOAD"):
                self.load(mission=cmd[4:].lstrip())
                break
            elif cmd == "BEGIN":
                self.begin()
                break
            elif cmd == "END":
                self.end()
                break
            elif cmd == "DESTROY":
                self.destroy()
                break
            return False
        return True

    def load(self, mission):
        self.mission = mission
        self.send("Loading mission {0}...".format(self.mission))
        self.send("Load bridges")
        self.send("Load static objects")
        self.send("##### House without collision "
            "(3do/Tree/Tree2.sim)")
        self.send("##### House without collision "
            "(3do/Buildings/Port/Floor/live.sim)")
        self.send("##### House without collision "
            "(3do/Buildings/Port/BaseSegment/live.sim)")
        self.status = MISSION_STATUS.LOADED
        self._send_status()

    def begin(self):
        if self.status == MISSION_STATUS.NOT_LOADED:
            self._mission_not_loaded()
        else:
            self.evt_log.start_log()
            self.status = MISSION_STATUS.PLAYING
            self._send_status()
            self.evt_log.enlog("Mission: {0} is Playing".format(self.mission))
            self.evt_log.enlog("Mission BEGIN")

    def end(self):
        if self.status == MISSION_STATUS.NOT_LOADED:
            self._mission_not_loaded()
        else:
            self.status = MISSION_STATUS.LOADED
            self._send_status()
            self.evt_log.enlog("Mission END")
            self.evt_log.stop_log()

    def destroy(self):
        if self.status == MISSION_STATUS.NOT_LOADED:
            self._mission_not_loaded()
        else:
            self.status = MISSION_STATUS.NOT_LOADED
            self.mission = None
            self.device_link.forget_everything()

    def _mission_not_loaded(self):
        self.send("ERROR mission: Mission NOT loaded")

    def _send_status(self):
        if self.status == MISSION_STATUS.NOT_LOADED:
            self.send("Mission NOT loaded")
        elif self.status == MISSION_STATUS.LOADED:
            self.send("Mission: {0} is Loaded".format(self.mission))
        elif self.status == MISSION_STATUS.PLAYING:
            self.send("Mission: {0} is Playing".format(self.mission))

    def stopService(self):
        self.mission = None
        return Service.stopService(self)


class StaticsService(Service):

    name = "statics"
    objects = None

    def __init__(self):
        self.objects = {}

    def spawn(self, name, pos=None):
        self.objects[name] = {
            'pos': pos or {'x': 0, 'y': 0, 'z': 0, },
            'state': OBJECT_STATE.ALIVE,
        }

    def destroy(self, name, attacker_name='landscape'):
        obj = self.objects[name]
        obj['state'] = OBJECT_STATE.DESTROYED
        self.evt_log.enlog("{0} destroyed by {1} at {2} {3}".format(
            name, attacker_name, obj['pos']['x'], obj['pos']['y']))

    def get_active(self):
        return [
            x for x in self.objects.keys()
            if self.objects[x]['state'] != OBJECT_STATE.DESTROYED
        ]


class DeviceLinkService(Service):

    name = "dl"
    pilots = None
    statics = None

    def __init__(self):
        self.forget_everything()

    def forget_everything(self):
        self.known_air = []
        self.known_static = []

    def refresh_radar(self):
        self.known_air = self.pilots.get_active()
        self.known_static = self.statics.get_active()

    def pilot_count(self):
        result = len(self.known_air)
        return OPCODE.PILOT_COUNT.make_command(result)

    def pilot_pos(self, arg):
        data = self._pos(known_container=self.known_air,
                         primary_container=self.pilots.pilots,
                         invalid_states=[PILOT_STATE.IDLE, PILOT_STATE.DEAD, ],
                         idx=arg, idx_append=True)
        return OPCODE.PILOT_POS.make_command(data) if data else None

    def static_count(self):
        result = len(self.known_static)
        return OPCODE.STATIC_COUNT.make_command(result)

    def static_pos(self, arg):
        data = self._pos(known_container=self.known_static,
                         primary_container=self.statics.objects,
                         invalid_states=[OBJECT_STATE.DESTROYED, ],
                         idx=arg)
        return OPCODE.STATIC_POS.make_command(data) if data else None

    def _pos(self, known_container, primary_container, invalid_states,
             idx, idx_append=False):
        if idx is None:
            return None
        try:
            key = known_container[int(idx)]
        except Exception:
            data = 'BADINDEX'
        else:
            handler = primary_container[key]
            if handler['state'] in invalid_states:
                data = 'INVALID'
            else:
                if idx_append:
                    key = "{:}_{:}".format(key, idx)
                pos = handler['pos']
                chunks = (key, pos['x'], pos['y'], pos['z'], )
                data = ';'.join([str(chunk) for chunk in chunks])
        finally:
            return ':'.join([idx, data, ])


class EventLogger(Service):

    def __init__(self, log_path=None, keep_log=True):
        self.log_path = log_path
        self.keep_log = keep_log
        self.log_file = None
        self.last_evt_time = None

    def enlog(self, line):
        if self.log_file is not None:
            self._do_log(line)
        else:
            LOG.info("Logging event into nowhere: \"{0}\"".format(line))

    def _do_log(self, line):
        evt_time = datetime.datetime.now()
        timestamp = self._get_formated_time(evt_time)
        _line = "[{0}] {1}\n".format(timestamp, line)
        self.log_file.write(_line)
        self.last_evt_time = evt_time

    def _get_formated_time(self, timestamp):
        """
        We do not need leading zero before hours, so we will replace it if it
        is present.
        """
        result = timestamp.strftime("%I:%M:%S %p").lstrip('0')
        if self._day_differs(timestamp):
            result = timestamp.strftime("%b %d, %Y ") + result
        return result

    def _day_differs(self, timestamp):
        return timestamp.day != self.last_evt_time.day \
            if self.last_evt_time is not None else True

    def start_log(self):
        self.stop_log()
        if self.log_path is not None:
            self.log_file = open(self.log_path, 'a' if self.keep_log else 'w')

    def stop_log(self):
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None

    def stopService(self):
        self.stop_log()
        return Service.stopService(self)
