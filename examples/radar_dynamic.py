# -*- coding: utf-8 -*-

import optparse

from twisted.application.internet import TimerService
from twisted.application.service import MultiService
from twisted.internet import defer, reactor

from il2ds_middleware.parser import (ConsoleParser, DeviceLinkParser,
    EventLogParser, )
from il2ds_middleware.protocol import ConsoleClientFactory, DeviceLinkClient
from il2ds_middleware import service


class PilotService(service.PilotBaseService):

    dlink = None

    def user_left(self, info):
        self.dlink.refresh_radar()

    def seat_occupied(self, info):
        self.dlink.refresh_radar()

    def was_killed(self, info):
        self.dlink.refresh_radar()

    def was_shot_down(self, info):
        self.dlink.refresh_radar()

    def went_to_menu(self, info):
        self.dlink.refresh_radar()

    def user_chat(self, info):
        print "%s says: %s" % info


class ObjectsService(service.ObjectsBaseService):
    pass


class MissionService(service.MissionService):

    dlink = None

    def began(self, info=None):
        service.MissionService.began(self, info)
        self.dlink.refresh_radar()

    def ended(self, info=None):
        service.MissionService.ended(self, info)
        self.dlink.refresh_radar()


class PilotRadarService(TimerService):

    dlink = None

    def __init__(self, interval=10):
        TimerService.__init__(self, interval, self.do_watch)

    def do_watch(self):
        self.dlink.all_pilots_pos().addCallbacks(
            self.on_response, self.on_error)

    def on_response(self, response):
        print "%s Got %s coordinates." % ("="*3, len(response))
        if not response:
            return
        print "{:^15} | {:^10} | {:^10} | {:^10}".format(
            "callsign", "x", "y", "z")
        for data in response:
            print "{:<15} | {:<10} | {:<10} | {:<10}".format(
                data['callsign'],
                data['pos']['x'], data['pos']['y'], data['pos']['z'], )

    def on_error(err):
        print "Getting pilots positions failed: %s." % err.value
        reactor.stop()


def parse_args():
    usage = """usage: %prog [--host=HOST] [--csport=CSPORT] [--dlport=DLPORT]
    [--frequency=FREQUENCY] --log=LOG"""
    parser = optparse.OptionParser(usage)

    help = "The host to connect to. Default is localhost."
    parser.add_option('--host', help=help, default='localhost')

    help = "The console port to connect to. Default is 20000."
    parser.add_option('--csport', type='int', default=20000, help=help)

    help = "The Device Link port to connect to. Default is 10000."
    parser.add_option('--dlport', type='int', default=10000, help=help)

    help = "Radar refreshing frequency. Default is 5 seconds."
    parser.add_option('--frequency', type='int', default=5, help=help)

    help = "Path to events log file."
    parser.add_option('--log', help=help)

    options, args = parser.parse_args()
    if not options.log:
        parser.error("Path to events log is not set.")
    return options


def main():
    options = parse_args()
    (host, port) = (options.host, options.csport)
    dl_address = (options.host, options.dlport)

    print "Working with"
    print "Server console on %s:%d." % (host, port)
    print "Device Link on %s:%d." % dl_address

    root = MultiService()
    pilots = PilotService()
    pilots.setServiceParent(root)

    objects = ObjectsService()
    objects.setServiceParent(root)

    radar = PilotRadarService(options.frequency)
    radar.setServiceParent(root)

    parser = EventLogParser((pilots, objects))
    log_watcher = service.LogWatchingService(options.log, parser=parser)
    missions = MissionService(log_watcher)
    missions.setServiceParent(root)

    def on_start(_):
        dl_client.refresh_radar()
        pilots.dlink = dl_client
        radar.dlink = dl_client
        missions.dlink = dl_client
        root.startService()
        root.client.mission_status()

    def on_connected(client):
        root.client = client
        pilots.client = client
        objects.client = client
        d = dl_client.on_start.addCallback(on_start)
        reactor.listenUDP(0, dl_client)
        return d

    def on_fail(err):
        print "Failed to connect: %s" % err.value
        reactor.stop()

    def on_connection_lost(err):
        print "Connection was lost."

    parser = ConsoleParser((pilots, missions))
    f = ConsoleClientFactory(parser)
    dl_client = DeviceLinkClient(dl_address, DeviceLinkParser())
    f.on_connecting.addCallbacks(on_connected, on_fail)
    f.on_connection_lost.addErrback(on_connection_lost)

    reactor.connectTCP(host, port, f)
    reactor.run()


if __name__ == '__main__':
    main()
