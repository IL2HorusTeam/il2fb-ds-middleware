# -*- coding: utf-8 -*-

from twisted.internet import defer, protocol
from twisted.protocols.basic import LineReceiver
from twisted.trial.unittest import FailTest, TestCase

from il2ds_middleware.ds_emulator.service import RootService
from il2ds_middleware.ds_emulator.protocol import (ConsoleFactory,
    ConsoleProtocol)


class ServerProtocol(ConsoleProtocol):

    def connectionLost(self, reason):
        ConsoleProtocol.connectionLost(self, reason)
        self.factory.on_connection_lost.callback(self)


class ClientProtocol(LineReceiver):

    def connectionMade(self):
        self.factory.on_connection_made.callback(self)

    def connectionLost(self, *a):
        self.factory.on_connection_lost.callback(self)

    def lineReceived(self, line):
        if self.factory.receiver:
            self.factory.receiver(line)


class ConsoleBaseTestCase(TestCase):

    def setUp(self):
        connected = defer.Deferred()
        self.client_disconnected = defer.Deferred()
        self.server_disconnected = defer.Deferred()

        self.server_port = self._listen_server(self.server_disconnected)
        self.client_connection = self._connect_client(
            connected, self.client_disconnected)

        return connected

    def _listen_server(self, d):
        self.sfactory = ConsoleFactory()
        self.sfactory.protocol = ServerProtocol
        self.sfactory.on_connection_lost = d

        self.sservice = RootService(self.sfactory)
        self.sfactory.service = self.sservice
        self.sservice.startService()

        from twisted.internet import reactor
        return reactor.listenTCP(0, self.sfactory, interface='127.0.0.1')

    def _connect_client(self, d1, d2):
        from twisted.internet import reactor
        self.cfactory = protocol.ClientFactory()
        self.cfactory.protocol = ClientProtocol
        self.cfactory.on_connection_made = d1
        self.cfactory.on_connection_lost = d2
        return reactor.connectTCP(
            '127.0.0.1', self.server_port.getHost().port, self.cfactory)

    def tearDown(self):
        d = defer.maybeDeferred(self.server_port.stopListening)
        self.client_connection.disconnect()
        self.cfactory.receiver = None
        return defer.gatherResults([
            d,
            self.client_disconnected,
            self.server_disconnected,
            self.sservice.stopService()])


class TestConnection(ConsoleBaseTestCase):

    def test_connect(self):
        self.assertEqual(len(self.sfactory.clients), 1)

    def test_disconnect(self):
        self.sfactory.on_connection_lost.addBoth(
            lambda _: self.assertEqual(len(self.sfactory.clients), 0))
        self.client_connection.disconnect()

    def test_receive_line(self):
        def got_line(line):
            timeout.cancel()
            return self.assertEqual(line, "test\\n")

        d = defer.Deferred()
        d.addCallback(got_line)
        self.cfactory.receiver = d.callback
        self.sfactory.broadcast_line("test")

        from twisted.internet import reactor
        timeout = reactor.callLater(0.1, d.errback, FailTest('Timed out'))

        return d


class TestPilots(ConsoleBaseTestCase):

    def test_join(self):
        pass
