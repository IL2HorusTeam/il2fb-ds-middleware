# -*- coding: utf-8 -*-
from twisted.internet import defer
from twisted.internet.protocol import Protocol, ServerFactory
from twisted.protocols import basic, loopback
from twisted.trial import unittest

from il2ds_middleware.ds_emulator.protocol import (ConsoleServer,
    ConsoleServerFactory, )


def add_watchdog(deferred, timeout=0.05):
    deferred.addCallback(lambda unused: watchdog.cancel())

    from twisted.internet import reactor
    watchdog = reactor.callLater(
        timeout, lambda: deferred.called or defer.timeout(deferred))


class ProtocolTestCase(unittest.TestCase):

    def test_connection(self):

        class TestProtocol(Protocol):
            transport = None

            def makeConnection(self, transport):
                self.transport = transport

        client = TestProtocol()
        server = ConsoleServer()
        server.factory = ConsoleServerFactory()

        d = server.factory.on_connected
        add_watchdog(d)

        loopback.loopbackAsync(server, client)
        self.assertIsNotNone(client.transport)

        return d
