# -*- coding: utf-8 -*-

from twisted.internet import defer, protocol
from twisted.protocols.basic import LineReceiver
from twisted.trial.unittest import FailTest, TestCase

from il2ds_middleware.ds_emulator.service import RootService
from il2ds_middleware.ds_emulator.protocol import (ConsoleFactory,
    ConsoleProtocol)


class ServerFactory(ConsoleFactory):

    def __init__(self):
        ConsoleFactory.__init__(self)
        self.on_connection_lost = defer.Deferred()

    def client_left(self, client):
        ConsoleFactory.client_left(self, client)
        self.on_connection_lost.callback(client)


class ClientProtocol(LineReceiver):

    def connectionMade(self):
        self.factory.client_joined(self)

    def connectionLost(self, reason):
        self.factory.client_left(self)

    def lineReceived(self, line):
        if self.factory.receiver:
            self.factory.receiver(line)


class ClientFactory(protocol.ClientFactory):

    protocol = ClientProtocol

    def __init__(self):
        self.clients = []
        self.on_connection_made = defer.Deferred()
        self.on_connection_lost = defer.Deferred()

    def client_joined(self, client):
        self.on_connection_made.callback(client)
        self.clients.append(client)

    def client_left(self, client):
        self.on_connection_lost.callback(client)
        self.clients.remove(client)

    def message(self, message):

        def do_message(message):
            for client in self.clients:
                client.sendLine(message)

        from twisted.internet import reactor
        reactor.callLater(0, do_message, message)


class ConsoleBaseTestCase(TestCase):

    def setUp(self):
        self.server_port = self._listen_server()
        self.client_connection, connected = self._connect_client()
        return connected

    def _listen_server(self):
        self.sfactory = ServerFactory()
        self.sservice = RootService(self.sfactory)
        self.sfactory.service = self.sservice
        self.sservice.startService()

        from twisted.internet import reactor
        return reactor.listenTCP(0, self.sfactory, interface="127.0.0.1")

    def _connect_client(self):
        self.cfactory = ClientFactory()
        from twisted.internet import reactor
        return (reactor.connectTCP(
            "127.0.0.1", self.server_port.getHost().port, self.cfactory),
            self.cfactory.on_connection_made)

    def tearDown(self):
        listening_stopped = defer.maybeDeferred(self.server_port.stopListening)
        self.client_connection.disconnect()
        self.cfactory.receiver = None
        return defer.gatherResults([
            listening_stopped,
            self.cfactory.on_connection_lost, self.sfactory.on_connection_lost,
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

        def on_timeout(_):
            d.errback(FailTest(
            'Timed out, remaining lines:\n\t'+'\n\t'.join(expected_responses)))

        from twisted.internet import reactor
        timeout = reactor.callLater(0.1, on_timeout, None)
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
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)
        self.sfactory.broadcast_line("test")
        return d

    def test_unknown_command(self):
        d = defer.Deferred()
        responses = ["Command not found: abracadabracadabr\\n", ]
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)
        self.cfactory.message("abracadabracadabr")
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


def expected_load_responses(path):
    return [
        "Loading mission {0}...\\n".format(path),
        "Load bridges\\n",
        "Load static objects\\n",
        "##### House without collision (3do/Tree/Tree2.sim)\\n",
        "##### House without collision (3do/Buildings/Port/Floor/live.sim)\\n",
        "##### House without collision (3do/Buildings/Port/BaseSegment/"
            "live.sim)\\n",
        "Mission: {0} is Loaded\\n".format(path)]


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
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)

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
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)
        self.srvc.join("user1", "192.168.1.2")
        self.srvc.join("user2", "192.168.1.3")
        self.srvc.leave("user1")
        self.srvc.leave("fake_user")
        return d


class TestMissions(ConsoleBaseTestCase):

    def setUp(self):
        r = super(TestMissions, self).setUp()
        self.srvc = self.sservice.getServiceNamed('missions')
        return r

    def tearDown(self):
        self.srvc = None
        return super(TestMissions, self).tearDown()

    def test_no_mission(self):
        d = defer.Deferred()
        responses = ["Mission NOT loaded\\n", ]
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)
        self.cfactory.message("mission")
        return d

    def test_load_mission(self):
        responses = expected_load_responses("net/dogfight/test.mis")
        responses.append(responses[-1])

        d = defer.Deferred()
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)
        self.cfactory.message("mission LOAD net/dogfight/test.mis")
        self.cfactory.message("mission")
        return d

    def test_begin_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n"]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append(responses[-1])

        d = defer.Deferred()
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)
        self.cfactory.message("mission BEGIN")
        self.cfactory.message("mission LOAD net/dogfight/test.mis")
        self.cfactory.message("mission BEGIN")
        self.cfactory.message("mission")
        return d

    def test_end_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n"]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append("Mission: net/dogfight/test.mis is Loaded\\n")

        d = defer.Deferred()
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)
        self.cfactory.message("mission END")
        self.cfactory.message("mission LOAD net/dogfight/test.mis")
        self.cfactory.message("mission BEGIN")
        self.cfactory.message("mission END")
        self.cfactory.message("mission END END END")
        self.cfactory.message("mission")
        return d

    def test_destroy_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n"]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append("Mission NOT loaded\\n")

        d = defer.Deferred()
        self.cfactory.receiver = self._get_expecting_line_receiver(responses, d)
        self.cfactory.message("mission DESTROY")
        self.cfactory.message("mission LOAD net/dogfight/test.mis")
        self.cfactory.message("mission DESTROY")
        self.cfactory.message("mission LOAD net/dogfight/test.mis")
        self.cfactory.message("mission BEGIN")
        self.cfactory.message("mission DESTROY")
        self.cfactory.message("mission")
        return d
