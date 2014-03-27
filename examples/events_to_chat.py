#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import optparse

from twisted.internet import defer, reactor

from il2ds_middleware.constants import MISSION_STATUS
from il2ds_middleware.parser import ConsoleParser, EventLogParser
from il2ds_middleware.protocol import ConsoleClientFactory
from il2ds_middleware import service


def wrap_time(line):
    return "<{0}> {1}".format(time.strftime('%H:%M:%S'), line)


def wrap_pos(line, info):
    return "{0} ({1}; {2})".format(
        line, info['pos']['x'], info['pos']['y'])


class PilotService(service.MutedPilotService):

    def user_joined(self, info):
        line = "Hello, {0} coming from {1}! We are watching you!".format(
            info['callsign'], info['ip'])
        self.client.chat_all(wrap_time(line))

    def user_left(self, info):
        line = "Bye-bye, {0} who came from {1}!".format(
            info['callsign'], info['ip'])
        self.client.chat_all(wrap_time(line))

    def user_chat(self, info):
        callsign, msg = info
        if msg.startswith('<'):
            self.client.chat_user("No commands are available!", callsign)

    def seat_occupied(self, info):
        line = "{0} selected seat #{1} in his {2}".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def selected_army(self, info):
        line = "{0} selected army {1}".format(info['callsign'], info['army'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def went_to_menu(self, info):
        line = "{0} went to menu".format(info['callsign'])
        self.client.chat_all(wrap_time(line))

    def weapons_loaded(self, info):
        line = "{0} loaded '{1}' weapons and {2}% fuel to his {3}".format(
            info['callsign'], info['loadout'], info['fuel'], info['aircraft'])
        self.client.chat_all(wrap_time(line))

    def was_killed(self, info):
        line = "{0}'s crew member #{1} was killed in {2}".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_killed_by_user(self, info):
        attacker = info['attacker']
        line = "{0}'s crew member #{1} was killed in {2} by {2} on {3}".format(
            info['callsign'], info['seat'], info['aircraft'],
            attacker['callsign'], attacker['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def took_off(self, info):
        line = "{0} took off on {1}".format(info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def landed(self, info):
        line = "{0} on {1} landed".format(info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def crashed(self, info):
        line = "{0} on {1} crashed".format(info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def damaged_self(self, info):
        line = "{0} on {1} damaged self".format(
            info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_damaged_by_user(self, info):
        attacker = info['attacker']
        line = "{0} on {1} was damaged by {2} on {3}".format(
            info['callsign'], info['aircraft'],
            attacker['callsign'], attacker['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_damaged_on_ground(self, info):
        line = "{0} on {1} was damaged on the ground".format(
            info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def shot_down_self(self, info):
        line = "{0} on {1} shot down self".format(
            info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_shot_down_by_user(self, info):
        attacker = info['attacker']
        line = "{0} on {1} was shot down by {2} on {3}".format(
            info['callsign'], info['aircraft'],
            attacker['callsign'], attacker['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_shot_down_by_static(self, info):
        line = "{0} on {1} was shot down by {2} object".format(
            info['callsign'], info['aircraft'], info['attacker'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def toggle_wingtip_smokes(self, info):
        line = "{0} on {1} turned smokes {2}".format(
            info['callsign'], info['aircraft'], info['value'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def toggle_landing_lights(self, info):
        line = "{0} on {1} turned landing lights {2}".format(
            info['callsign'], info['aircraft'], info['value'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def bailed_out(self, info):
        line = "{0}'s crew member #{1} bailed out from {2}".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def parachute_opened(self, info):
        line = "{0}'s' crew member's #{1} from {2} parachute opened".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_captured(self, info):
        line = "{0}'s crew member #{1} from {2} was captured".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_wounded(self, info):
        line = "{0}'s crew member #{1} from {2} was wounded".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_heavily_wounded(self, info):
        line = "{0}'s crew member #{1} from {2} was heavily wounded".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))


class ObjectsService(service.MutedObjectsService):

    def building_destroyed_by_user(self, info):
        line = "Building {0} was destroyed by {1} on {2}".format(
            info['building'], info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def tree_destroyed_by_user(self, info):
        line = "Tree {0} was destroyed by {1} on {2}".format(
            info['tree'], info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def static_destroyed_by_user(self, info):
        line = "Static {0} was destroyed by {1} on {2}".format(
            info['static'], info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def bridge_destroyed_by_user(self, info):
        line = "Bridge {0} was destroyed by {1} on {2}".format(
            info['bridge'], info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))


class MissionsService(service.MissionsService):

    def began(self, (status, mission)):
        self.client.chat_all(
            wrap_time("Mission \"{0}\" is playing.".format(mission)))
        service.MissionsService.began(self, (status, mission))

    def ended(self, (status, mission)):
        service.MissionsService.ended(self, (status, mission))
        self.client.chat_all(
            wrap_time("Mission \"{0}\" has ended.".format(mission)))

    def was_won(self, info):
        line = "Mission was won by {0} army.".format(info['army'])
        self.client.chat_all(wrap_time(line, info))

    def target_end(self, info):
        line = "Target #{0} {1}.".format(info['number'], info['result'])
        self.client.chat_all(wrap_time(line, info))


def parse_args():
    usage = """usage: %prog [--host=HOST] [--port=CSPORT] --log=LOG"""
    parser = optparse.OptionParser(usage)

    help = "The host to connect to. Default is localhost."
    parser.add_option('--host', help=help, default='localhost')

    help = "The console port to connect to. Default is 20000."
    parser.add_option('--port', type='int', default=20000, help=help)

    help = "Path to events log file."
    parser.add_option('--log', help=help)

    options, args = parser.parse_args()
    if not options.log:
        parser.error("Path to events log is not set.")
    return options


def main():
    options = parse_args()
    print "Working with server console on %s:%d." % (
        options.host, options.port)

    def on_connected(client):
        missions.client = client
        pilots.client = client
        objects.client = client
        missions.startService()
        pilots.startService()
        client.mission_status()

    def on_fail(err):
        print "Failed to connect: %s" % err.value
        reactor.stop()

    def on_connection_lost(err):
        print "Connection was lost."

    pilots = PilotService()
    objects = ObjectsService()

    log_watcher = service.LogWatchingService(options.log)
    missions = MissionsService(log_watcher)
    p = EventLogParser((pilots, objects, missions))
    log_watcher.set_parser(p)

    p = ConsoleParser((pilots, missions))
    f = ConsoleClientFactory(parser=p, timeout_value=1)
    f.on_connecting.addCallbacks(on_connected, on_fail)
    f.on_connection_lost.addErrback(on_connection_lost)
    reactor.connectTCP(options.host, options.port, f)
    reactor.run()


if __name__ == '__main__':
    main()
