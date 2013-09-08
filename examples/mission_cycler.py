# -*- coding: utf-8 -*-

import optparse

from twisted.application.internet import TimerService
from twisted.application.service import Service
from twisted.internet import defer, reactor

from zope.interface import implementer

from il2ds_middleware.interface.service import IMissionService
from il2ds_middleware.parser import ConsoleParser
from il2ds_middleware.protocol import ConsoleClientFactory
from il2ds_middleware.service import PilotBaseService, MissionBaseService


class PilotService(PilotBaseService):

    def __init__(self, missions):
        self.missions = missions

    def user_chat(self, (callsign, msg)):
        if msg == "<timeleft":
            self.client.chat_user(self.missions.time_left_str(), callsign)


class MissionService(MissionBaseService):

    client = None

    def __init__(self, mission, duration):
        self.mission = mission
        self.duration = duration
        self.time_checker = TimerService(1, self.check_time)
        self.time_left = 0
        self.time_to_notification = 0

    def startService(self):
        Service.startService(self)
        return self.reload_mission()

    def reload_mission(self):

        def on_destroyed(_):
            self.client.chat_all(
                "Loading mission \"{:}\".".format(self.mission))
            return self.client.mission_load(self.mission).addCallback(
                on_loaded)

        def on_loaded(_):
            return self.client.mission_begin().addCallback(self.on_playing)

        return self.client.mission_destroy().addCallback(on_destroyed)

    def on_playing(self, *args):
        self.client.chat_all(
            "Mission \"{:}\" is playing.".format(self.mission))
        self.time_left = self.duration
        self.time_to_notification == 0
        self.time_checker.startService()

    def check_time(self):
        if self.time_left == 0:
            self.time_checker.stopService()
            self.client.chat_all("Mission is ended.")
            return self.reload_mission()
        if self.time_to_notification == 0:
            self.client.chat_all(self.time_left_str())
            if not self.check_notification_time(15*60):
                if not self.check_notification_time(5*60):
                    if not self.check_notification_time(60):
                        if not self.check_notification_time(15):
                            if not self.check_notification_time(10, 5):
                                self.time_to_notification = 1
        self.time_left -= 1
        self.time_to_notification -= 1

    def time_left_str(self):
        m, s = divmod(self.time_left, 60)
        h, m = divmod(m, 60)
        return "Mission time left: %d:%02d:%02d" % (h, m, s)

    def check_notification_time(self, time_range, new_value=None):
        if self.time_left <= time_range:
            return False
        new_value = new_value or time_range
        value = self.time_left % new_value
        if value == 0:
            value = new_value
        self.time_to_notification = value
        return True


def parse_args():
    usage = """usage: %prog [--host=HOST] [--port=CSPORT]
    [--duration=DURATION] --mission=MISSION"""
    parser = optparse.OptionParser(usage)

    help = "The host to connect to. Default is localhost."
    parser.add_option('--host', help=help, default='localhost')

    help = "The console port to connect to. Default is 20000."
    parser.add_option('--port', type='int', default=20000, help=help)

    help = "Mission duration in seconds. Default is 3600."
    parser.add_option('--duration', type='int', default=3600, help=help)

    help = "Misssion to play (e.g., net/dogfight/test.mis)."
    parser.add_option('--mission', help=help)

    options, args = parser.parse_args()
    if not options.mission:
        parser.error("Misssion to play is not set.")
    return options


def main():
    options = parse_args()
    print "Working with server console on %s:%d." % (
        options.host, options.port)
    print "Rotating mission \"{:}\" with duration of {:} seconds.".format(
        options.mission, options.duration)

    def on_connected(client):
        missions.client = client
        pilots.client = client
        missions.startService()
        pilots.startService()

    def on_fail(err):
        print "Failed to connect: %s" % err.value
        reactor.stop()

    def on_connection_lost(err):
        print "Connection was lost."

    missions = MissionService(options.mission, options.duration)
    pilots = PilotService(missions)

    p = ConsoleParser((pilots, missions))
    f = ConsoleClientFactory(parser=p, timeout_value=1)
    f.on_connecting.addCallbacks(on_connected, on_fail)
    f.on_connection_lost.addErrback(on_connection_lost)
    reactor.connectTCP(options.host, options.port, f)
    reactor.run()


if __name__ == '__main__':
    main()
