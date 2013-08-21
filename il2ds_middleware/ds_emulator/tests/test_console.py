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
        return reactor.listenTCP(0, self.sfactory, interface="127.0.0.1")

    def _connect_client(self, d1, d2):
        from twisted.internet import reactor
        self.cfactory = protocol.ClientFactory()
        self.cfactory.protocol = ClientProtocol
        self.cfactory.on_connection_made = d1
        self.cfactory.on_connection_lost = d2
        return reactor.connectTCP(
            "127.0.0.1", self.server_port.getHost().port, self.cfactory)

    def tearDown(self):
        listening_stopped = defer.maybeDeferred(self.server_port.stopListening)
        self.client_connection.disconnect()
        self.cfactory.receiver = None
        return defer.gatherResults([
            listening_stopped,
            self.client_disconnected, self.server_disconnected,
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

        from twisted.internet import reactor
        timeout = reactor.callLater(0.1, d.errback, FailTest('Timed out'))

        self.sfactory.broadcast_line("test")
        return d


class TestPilots(ConsoleBaseTestCase):

    def test_join(self):

        def expected_responses(channel, callsign, ip, user_port):
            return [
                "socket channel '{0}' start creating: ip {1}:{2}\\n".format(
                    channel, ip, user_port)
                , "Chat: --- {0} joins the game.\\n".format(callsign)
                , "socket channel '{0}', ip {1}:{2}, {3}, " \
                    "is complete created.\\n".format(
                    channel, ip, user_port, callsign)]

        def got_line(line):
            try:
                self.assertEqual(line, responses.pop(0))
            except AssertionError, e:
                timeout.cancel()
                d.errback(e)
            else:
                if responses:
                    return
                timeout.cancel()
                d.callback(None)

        def check_pilots_count(_):
            self.assertEqual(len(srvc.pilots), 2)

        self.cfactory.receiver = got_line
        srvc = self.sservice.getServiceNamed('pilots')

        responses = expected_responses(
            1, "user1", "192.168.1.2", srvc.port)
        responses.extend(expected_responses(
            3, "user2", "192.168.1.3", srvc.port))

        srvc.join("user1", "192.168.1.2")
        srvc.join("user2", "192.168.1.3")

        d = defer.Deferred()
        d.addCallback(check_pilots_count)
        from twisted.internet import reactor
        timeout = reactor.callLater(0.1, d.errback, FailTest('Timed out'))
        return d
