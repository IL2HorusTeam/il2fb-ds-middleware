# -*- coding: utf-8 -*-

import optparse

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


def main():

    def on_pos(response):
        print "Got %s coordinates" % len(response)
        for data in response:
            print "{0}: x={1}; y={2}; z={3}".format(
                data['callsign'],
                data['pos']['x'], data['pos']['y'], data['pos']['z'], )

    def on_err(err):
        print "Getting pilots positions failed: %s." % err.value

    def do_stop(_):
        from twisted.internet import reactor
        reactor.stop()

    def on_start(_):
        client.refresh_radar()
        return client.all_pilots_pos().addCallbacks(
            on_pos, on_err).addBoth(do_stop)

    address = parse_args()
    print "Working with Device Link on %s:%s." % address

    client = DeviceLinkClient(address, DeviceLinkParser())
    client.on_start.addCallback(on_start)

    from twisted.internet import reactor
    reactor.listenUDP(0, client)
    reactor.run()


if __name__ == '__main__':
    main()
