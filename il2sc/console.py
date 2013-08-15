# -*- coding: utf-8 -*-

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log


class ConsoleProtocol(LineOnlyReceiver):

    def lineReceived(self, line):
        # TODO:


class ConsoleClientFactory(ClientFactory):
    protocol = ConsoleProtocol

    def clientConnectionFailed(self, connector, reason):
        log.err("Connection failed: %s" % reason)
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        log.err("Connection lost: %s" % reason)
        reactor.stop()
