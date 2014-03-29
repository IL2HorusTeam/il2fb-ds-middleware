#!/usr/bin/env python
# -*- coding: utf-8 -*-
import optparse
import os

from twisted.application.internet import TimerService
from twisted.application.service import MultiService
from twisted.internet import reactor

from il2ds_middleware.parser import (ConsoleParser, DeviceLinkParser,
    EventLogParser, )
from il2ds_middleware.protocol import ConsoleClientFactory, DeviceLinkClient
from il2ds_middleware.service import (ClientServiceMixin, LogWatchingService,
    MissionsService as DefaultMissionsService, MutedPilotsService,
    MutedObjectsService, )


class PilotsService(MutedPilotsService):

    @ClientServiceMixin.radar_refresher
    def passthrough(self, info):
        pass

    user_left = weapons_loaded = was_killed = was_killed_by_user = \
    shot_down_self = was_shot_down_by_user = was_shot_down_by_static = \
    bailed_out = went_to_menu = passthrough

    def user_chat(self, (callsign, message)):
        print "{0} says: {1}".format(callsign, message)


class MissionsService(DefaultMissionsService):

    @ClientServiceMixin.radar_refresher
    def began(self, info=None):
        DefaultMissionsService.began(self, info)

    def ended(self, info=None):
        DefaultMissionsService.ended(self, info)


class PilotRadarService(TimerService):

    dl_client = None

    def __init__(self, period=10):
        TimerService.__init__(self, period, self.do_watch)

    def do_watch(self):
        self.dl_client.all_pilots_pos().addCallbacks(self.on_response,
                                                     self.on_failure)

    def on_response(self, response):
        print "=== Number of received coordinates: {0}".format(len(response))

        if not response:
            return
        print "{:^15} | {:^10} | {:^10} | {:^10}".format(
              "callsign", "x", "y", "z")
        for data in response:
            print "{:<15} | {:<10} | {:<10} | {:<10}".format(
                  data['callsign'],
                  data['pos']['x'], data['pos']['y'], data['pos']['z'], )

    def on_failure(self, failure):
        print "Failed to get pilots' coordinates: %s." % failure.value
        reactor.stop()


def parse_args():
    usage = """usage: %prog [--host=HOST] [--cl_port=CL_PORT] [--dl_port=DL_PORT]
    [--period=PERIOD] --log=LOG"""
    parser = optparse.OptionParser(usage)

    help = "The host to connect to. Default is localhost."
    parser.add_option('--host', help=help, default='localhost')

    help = "The console port to connect to. Default is 20000."
    parser.add_option('--cl_port', type='int', default=20000, help=help)

    help = "The Device Link port to connect to. Default is 10000."
    parser.add_option('--dl_port', type='int', default=10000, help=help)

    help = "Period of radar refresh. Default is 5 seconds."
    parser.add_option('--period', type='int', default=5, help=help)

    help = "Path to events log file."
    parser.add_option('--log', help=help)

    options, args = parser.parse_args()

    if not options.log:
        parser.error("Path to events log is not set.")
    if not os.path.exists(options.log) or not os.path.isfile(options.log):
        parser.error("Invalid path to events log.")

    return options


if __name__ == '__main__':

    def on_device_link_started(unused):
        dl_client.refresh_radar()

        pilots.dl_client = dl_client
        radar.dl_client = dl_client
        missions.dl_client = dl_client

        root.startService()
        root.cl_client.mission_status()

    def on_connection_done(cl_client):
        root.cl_client = cl_client
        pilots.cl_client = cl_client
        objects.cl_client = cl_client

        d = dl_client.on_start.addCallback(on_device_link_started)
        reactor.listenUDP(0, dl_client)
        return d

    def on_connection_failed(failure):
        print "Failed to connect: %s" % failure.value
        reactor.stop()

    def on_connection_lost(failure):
        print "Connection was lost: %s" % failure.value

    options = parse_args()
    (host, port) = (options.host, options.cl_port)
    dl_address = (options.host, options.dl_port)

    print "Working with"
    print "Server console on %s:%d." % (host, port)
    print "Device Link on %s:%d." % dl_address

    root = MultiService()
    radar = PilotRadarService(options.period)
    radar.setServiceParent(root)

    pilots = PilotsService()
    pilots.setServiceParent(root)

    objects = MutedObjectsService()
    objects.setServiceParent(root)

    log_watcher = LogWatchingService(options.log)
    missions = MissionsService(log_watcher)
    parser = EventLogParser((pilots, objects, missions))
    log_watcher.set_parser(parser)
    missions.setServiceParent(root)

    parser = ConsoleParser((pilots, missions))
    f = ConsoleClientFactory(parser)
    f.on_connecting.addCallbacks(on_connection_done, on_connection_failed)
    f.on_connection_lost.addErrback(on_connection_lost)

    dl_client = DeviceLinkClient(dl_address, DeviceLinkParser())

    reactor.connectTCP(host, port, f)
    reactor.run()
