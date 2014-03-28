#!/usr/bin/env python
# -*- coding: utf-8 -*-
import optparse

from twisted.internet import reactor

from il2ds_middleware.parser import DeviceLinkParser
from il2ds_middleware.protocol import DeviceLinkClient


def parse_args():
    usage = """usage: %prog [hostname]:port"""
    parser = optparse.OptionParser(usage)

    help = "The host to connect to. Default is localhost."
    parser.add_option('--host', help=help, default='localhost')

    help = "The port to connect to. Default is 10000."
    parser.add_option('--port', type='int', default=10000, help=help)

    options, args = parser.parse_args()
    return (options.host, options.port)


def on_positions(response):
    print "Number of received coordinates: {count}".format(count=len(response))
    for data in response:
        print "{0}: x={1}; y={2}; z={3}".format(
            data['callsign'],
            data['pos']['x'], data['pos']['y'], data['pos']['z'], )


def errback(failure):
    print "Failed to get pilots coordinates: %s." % failure.value


def on_start(client):
    client.refresh_radar()
    return client.all_pilots_pos().addCallbacks(
        on_positions, errback).addBoth(
        lambda unused: reactor.stop())


if __name__ == '__main__':
    address = parse_args()
    print "Working with Device Link on %s:%s." % address

    client = DeviceLinkClient(address, DeviceLinkParser())
    client.on_start.addCallback(on_start)

    reactor.listenUDP(0, client)
    reactor.run()
