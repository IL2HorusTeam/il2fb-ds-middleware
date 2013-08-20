# -*- coding: utf-8 -*-

from twisted.internet import defer, protocol
from twisted.protocols.basic import LineReceiver
from twisted.trial.unittest import TestCase

from il2ds_middleware.ds_emulator.service import RootService
from il2ds_middleware.ds_emulator.protocol import (ConsoleFactory,
    ConsoleProtocol)


class ServerProtocol(ConsoleProtocol):

    def connectionLost(self, reason):
        ConsoleProtocol.connectionLost(self, reason)
        self.factory.onConnectionLost.callback(self)


class FakeClient(LineReceiver):

    def lineReceived(self, line):
        pass

    def connectionMade(self):
        self.factory.onConnectionMade.callback(self)

    def connectionLost(self, *a):
        self.factory.onConnectionLost.callback(self)


class TestConsole(TestCase):

    def setUp(self):
        connected = defer.Deferred()
        self.client_disconnected = defer.Deferred()
        self.server_disconnected = defer.Deferred()

        self.server_port = self._listen_server(self.server_disconnected)
        self.client_connection = self._connect_client(
            connected, self.client_disconnected)

        return connected

    def _listen_server(self, d):
        from twisted.internet import reactor
        self.sfactory = ConsoleFactory()
        self.sfactory.protocol = ServerProtocol
        self.sfactory.onConnectionLost = d
        return reactor.listenTCP(0, self.sfactory)

    def _connect_client(self, d1, d2):
        from twisted.internet import reactor
        f = protocol.ClientFactory()
        f.protocol = FakeClient
        f.onConnectionMade = d1
        f.onConnectionLost = d2
        return reactor.connectTCP(
            'localhost', self.server_port.getHost().port, f)

    def tearDown(self):
        d = defer.maybeDeferred(self.server_port.stopListening)
        self.client_connection.disconnect()
        return defer.gatherResults([
            d,
            self.client_disconnected,
            self.server_disconnected])

    def test_connect(self):
        pass
