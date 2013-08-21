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

    def _get_expecting_line_receiver(self, expected_responses, d):

        def got_line(line):
            try:
                self.assertEqual(line, expected_responses.pop(0))
            except Exception as e:
                timeout.cancel()
                d.errback(e)
            else:
                if expected_responses:
                    return
                timeout.cancel()
                d.callback(None)

        from twisted.internet import reactor
        timeout = reactor.callLater(0.1, d.errback, FailTest('Timed out'))
        return got_line


class TestConnection(ConsoleBaseTestCase):

    def test_connect(self):
        self.assertEqual(len(self.sfactory.clients), 1)

    def test_disconnect(self):
        self.sfactory.on_connection_lost.addBoth(
            lambda _: self.assertEqual(len(self.sfactory.clients), 0))
        self.client_connection.disconnect()

    def test_receive_line(self):
        d = defer.Deferred()
        responses = ["test\\n", ]
        self.cfactory.receiver = self._get_expecting_line_receiver(
            responses, d)
        self.sfactory.broadcast_line("test")
        return d


def expected_join_responses(channel, callsign, ip, port):
    return [
        "socket channel '{0}' start creating: ip {1}:{2}\\n".format(
            channel, ip, port),
        "Chat: --- {0} joins the game.\\n".format(callsign),
        "socket channel '{0}', ip {1}:{2}, {3}, "
        "is complete created.\\n".format(
            channel, ip, port, callsign)]


def expected_leave_responses(channel, callsign, ip, port):
    return [
        "socketConnection with {0}:{1} on channel {2} lost.  "
        "Reason: \\n".format(
            ip, port, channel),
        "Chat: --- {0} has left the game.\\n".format(
            callsign)]


class TestPilots(ConsoleBaseTestCase):

    def setUp(self):
        r = super(TestPilots, self).setUp()
        self.srvc = self.sservice.getServiceNamed('pilots')
        return r

    def tearDown(self):
        self.srvc = None
        return super(TestPilots, self).tearDown()

    def _get_pilots_count_checker(self, expected_count):
        def check(_):
            self.assertEqual(len(self.srvc.pilots), expected_count)
        return check

    def test_join(self):
        responses = expected_join_responses(
            1, "user1", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user2", "192.168.1.3", self.srvc.port))

        d = defer.Deferred()
        d.addCallback(self._get_pilots_count_checker(2))
        self.cfactory.receiver = self._get_expecting_line_receiver(
            responses, d)

        self.srvc.join("user1", "192.168.1.2")
        self.srvc.join("user2", "192.168.1.3")
        return d

    def test_leave(self):
        responses = expected_join_responses(
            1, "user1", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user2", "192.168.1.3", self.srvc.port))
        responses.extend(expected_leave_responses(
            1, "user1", "192.168.1.2", self.srvc.port))

        d = defer.Deferred()
        d.addCallback(self._get_pilots_count_checker(1))
        self.cfactory.receiver = self._get_expecting_line_receiver(
            responses, d)

        self.srvc.join("user1", "192.168.1.2")
        self.srvc.join("user2", "192.168.1.3")
        self.srvc.leave("user1")
        return d
