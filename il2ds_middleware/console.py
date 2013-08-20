# -*- coding: utf-8 -*-

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log


class DSConsoleProtocol(LineOnlyReceiver):

    def connectionMade(self):
        log.msg("Connection established with {0}".format(
            self.transport.getPeer()))

    def connectionLost(self, reason):
        log.err("Connection with {0} lost: {1}".format(
            self.transport.getPeer(), reason))

    def lineReceived(self, line):
        if line == '' or line == "exit\\n":
            log.err("Game server is shut down")
            reactor.stop()
            return
        if line.startswith("<consoleN>"):
            return
        if line.endswith("\\n"):
            line = line[:-2]
        if line.startswith("\\u0020"):
            line = " " + line[6:]
        # TODO:


class DSConsoleFactory(ClientFactory):

    protocol = ConsoleProtocol

    def clientConnectionFailed(self, connector, reason):
        log.err("Connection failed: %s" % reason)
