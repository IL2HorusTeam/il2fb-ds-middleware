# -*- coding: utf-8 -*-

import time
import optparse

from twisted.internet import defer, reactor

from il2ds_middleware.parser import ConsoleParser, EventLogParser
from il2ds_middleware.protocol import ConsoleClientFactory
from il2ds_middleware import service


def wrap_time(line):
    return "{:} | {:}".format(time.strftime('%H:%M:%S'), line)

def wrap_pos(line, info):
    return "{:} | x, y = {:}, {:}".format(
        line, info['pos']['x'], info['pos']['y'])


class PilotService(service.PilotBaseService):

    def user_join(self, info):
        line = "Hello, {:} coming from {:}! We are watching you!".format(
            info['callsign'], info['ip'])
        self.client.chat_all(wrap_time(line))

    def user_left(self, info):
        line = "Bye-bye, {:} who came from {:}!".format(
            info['callsign'], info['ip'])
        self.client.chat_all(wrap_time(line))

    def user_chat(self, info):
        callsign, msg = info
        if msg.startswith('<'):
            self.client.chat_user("No commands are available!", callsign)

    def selected_army(self, info):
        line = "{:} selected army {:}".format(info['callsign'], info['army'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def went_to_menu(self, info):
        line = "{:} went to menu".format(info['callsign'])
        self.client.chat_all(wrap_time(line))

    def seat_occupied(self, info):
        line = "{:} selected seat #{:} in his {:}".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def weapons_loaded(self, info):
        line = "{:} loaded '{:}' weapons and {:}% fuel to his {:}".format(
            info['callsign'], info['weapons'], info['fuel'], info['aircraft'])
        self.client.chat_all(wrap_time(line))

    def bailed_out(self, info):
        line = "{:}'s crew member #{:} bailed out from {:}".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def removed(self, info):
        line = "{:}'s aircraft {:} was removed".format(
            info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_killed(self, info):
        line = "{:}'s crew member #{:} was killed in {:}".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_shot_down(self, info):
        attacker = info['attacker']
        attacker_info = "{:} on {:}".format(
            attacker['callsign'], attacker['aircraft']
        ) if attacker['is_user'] else attacker['name']
        victim = info['victim']
        line = "{:} on {:} was shot down by {:}".format(
            victim['callsign'], victim['aircraft'], attacker_info)
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def in_flight(self, info):
        line = "{:} took off on {:}".format(
            info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def landed(self, info):
        actor_info = "{:} on {:}".format(
            info['callsign'], info['aircraft']
        ) if info['is_user'] else info['name']
        line = "{:} landed".format(actor_info)
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def damaged(self, info):
        attacker = info['attacker']
        attacker_info = "{:} on {:}".format(
            attacker['callsign'], attacker['aircraft']
        ) if attacker['is_user'] else attacker['name']
        victim = info['victim']
        line = "{:} on {:} was damaged by {:}".format(
            victim['callsign'], victim['aircraft'], attacker_info)
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def damaged_on_ground(self, info):
        line = "{:} damaged on the ground on {:}".format(
            info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def turned_wingtip_smokes(self, info):
        line = "{:} on {:} turned smokes {:}".format(
            info['callsign'], info['aircraft'], info['state'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def crashed(self, info):
        line = "{:} on {:} crashed".format(info['callsign'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_captured(self, info):
        line = "{:}'s crew member #{:} from {:} was captured".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_wounded(self, info):
        line = "{:}'s crew member #{:} from {:} was wounded".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))

    def was_heavily_wounded(self, info):
        line = "{:}'s crew member #{:} from {:} was heavily wounded".format(
            info['callsign'], info['seat'], info['aircraft'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))


class ObjectsService(service.ObjectsBaseService):

    def was_destroyed(self, info):
        line = "{:} was destroyed by {:}".format(
            info['victim'], info['attacker'])
        self.client.chat_all(wrap_time(wrap_pos(line, info)))


class MissionService(service.MissionService):

    def began(self, info=None):
        if self.status is not None:
            status, mission = info
            self.client.chat_all(
                wrap_time("Mission \"{:}\" has started.".format(mission)))
        service.MissionService.began(self, info)

    def ended(self, info=None):
        service.MissionService.ended(self, info)
        status, mission = info
        self.client.chat_all(
            wrap_time("Mission \"{:}\" has ended.".format(mission)))


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

    p = EventLogParser((pilots, objects))
    log_watcher = service.LogWatchingService(options.log, parser=p)
    missions = MissionService(log_watcher)

    p = ConsoleParser((pilots, missions))
    f = ConsoleClientFactory(parser=p, timeout_value=1)
    f.on_connecting.addCallbacks(on_connected, on_fail)
    f.on_connection_lost.addErrback(on_connection_lost)
    reactor.connectTCP(options.host, options.port, f)
    reactor.run()


if __name__ == '__main__':
    main()
