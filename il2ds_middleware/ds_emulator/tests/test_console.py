# -*- coding: utf-8 -*-
from twisted.internet import defer
from twisted.internet.protocol import Protocol
from twisted.protocols import basic, loopback
from twisted.python.failure import Failure
from twisted.trial import unittest

from il2ds_middleware.ds_emulator.protocol import (ConsoleServer,
    ConsoleServerFactory, )
from il2ds_middleware.ds_emulator.service import RootService


def add_watchdog(deferred, timeout=None, callback=None):

    def on_error(failure):
        watchdog.cancel()
        return failure

    deferred.addCallbacks(lambda unused: watchdog.cancel(), on_error)

    def on_timeout():
        if deferred.called:
            return
        if callback is not None:
            callback()
        else:
            defer.timeout(deferred)

    from twisted.internet import reactor
    watchdog = reactor.callLater(timeout or 0.05, on_timeout)


class ConnectionTestCase(unittest.TestCase):

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

    def test_disconnection(self):
        client = Protocol()
        server = ConsoleServer()
        server.factory = ConsoleServerFactory()

        d = server.factory.on_connection_lost
        add_watchdog(d)

        loopback.loopbackAsync(server, client)
        client.transport.loseConnection()

        return d


class UnexpectedLineError(Exception):

    def __init__(self, line):
        self.line = line

    def __str__(self):
        return "Unexpected line: {0}".format(self.line)


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.console_client = basic.LineReceiver()
        self.console_client.lineReceived = lambda line: None

        self.server = ConsoleServer()
        self.server.factory = ConsoleServerFactory()

        self.service = RootService()

        self.service.client = self.server
        self.server.service = self.service

        self.service.startService()
        loopback.loopbackAsync(self.server, self.console_client)

    def tearDown(self):
        self.server.transport.loseConnection()
        return self.service.stopService()

    def _get_expecting_line_receiver(self, expected_lines=None, timeout=None):
        expected_lines = expected_lines[:] if expected_lines else []

        def got_line(line):
            if d.called:
                return
            if expected_lines:
                try:
                    self.assertEqual(line, expected_lines.pop(0))
                except Exception as e:
                    d.errback(e)
                else:
                    if not expected_lines:
                        d.callback(None)
            else:
                d.errback(Failure(UnexpectedLineError(line)))

        def on_timeout():
            d.errback(unittest.FailTest(
                "Timed out, remaining lines:\n\t{1}".format(
                "\n\t".join(expected_lines))))

        d = defer.Deferred()
        add_watchdog(d, timeout, on_timeout)
        return got_line, d

    def expect_console_lines(self, expected_lines=None, timeout=None):
        self.console_client.lineReceived, d = \
            self._get_expecting_line_receiver(expected_lines, timeout)
        return d


class CommonsTestCase(BaseTestCase):

    def test_receive_line(self):
        d = self.expect_console_lines([
            "test\\n",
        ])
        self.server.message("test")
        return d

    def test_unknown_command(self):
        d = self.expect_console_lines([
            "Command not found: abracadabracadabr\\n",
        ])
        self.console_client.sendLine("abracadabracadabr")
        return d

    def test_unexpected_line(self):
        d = self.expect_console_lines()
        self.server.message("test")
        return self.assertFailure(d, UnexpectedLineError)

    def test_expected_line_mismatch(self):
        d = self.expect_console_lines([
            "foo\\n",
        ])
        self.server.message("bar")
        return self.assertFailure(d, AssertionError)

    @defer.inlineCallbacks
    def test_server_info(self):
        d = self.expect_console_lines([
            "Type: Local server\\n",
            "Name: Server\\n",
            "Description: \\n",
        ])
        self.console_client.sendLine("server")
        yield d

        self.service.set_server_info("Test server",
                                     "This is a server emulator")

        d = self.expect_console_lines([
            "Type: Local server\\n",
            "Name: Test server\\n",
            "Description: This is a server emulator\\n",
        ])
        self.console_client.sendLine("server")
        yield d


def expected_join_responses(channel, callsign, ip, port):
    return [
        "socket channel '{0}' start creating: ip {1}:{2}\\n".format(
            channel, ip, port),
        "Chat: --- {0} joins the game.\\n".format(callsign),
        "socket channel '{0}', ip {1}:{2}, {3}, "
        "is complete created.\\n".format(
            channel, ip, port, callsign),
    ]


def expected_leave_responses(channel, callsign, ip, port):
    return [
        "socketConnection with {0}:{1} on channel {2} lost.  "
        "Reason: \\n".format(
            ip, port, channel),
        "Chat: --- {0} has left the game.\\n".format(
            callsign),
    ]


def expected_kick_responses(channel, callsign, ip, port):
    return [
        "socketConnection with {0}:{1} on channel {2} lost.  "
        "Reason: You have been kicked from the server.\\n".format(
            ip, port, channel),
        "Chat: --- {0} has left the game.\\n".format(
            callsign),
    ]


def expected_load_responses(path):
    return [
        "Loading mission {0}...\\n".format(path),
        "Load bridges\\n",
        "Load static objects\\n",
        "##### House without collision (3do/Tree/Tree2.sim)\\n",
        "##### House without collision (3do/Buildings/Port/Floor/live.sim)\\n",
        "##### House without collision (3do/Buildings/Port/BaseSegment/"
            "live.sim)\\n",
        "Mission: {0} is Loaded\\n".format(path),
    ]


class PilotsTestCase(BaseTestCase):

    def setUp(self):
        d = super(PilotsTestCase, self).setUp()
        self.pilots = self.service.getServiceNamed('pilots')
        return d

    def test_join(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.pilots.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.pilots.port))

        d = self.expect_console_lines(responses)
        self.pilots.join("user0", "192.168.1.2")
        self.pilots.join("user1", "192.168.1.3")
        return d

    @defer.inlineCallbacks
    def test_leave(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.pilots.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.pilots.port))
        responses.extend(expected_leave_responses(
            1, "user0", "192.168.1.2", self.pilots.port))

        d = self.expect_console_lines(responses)
        self.pilots.join("user0", "192.168.1.2")
        self.pilots.join("user1", "192.168.1.3")
        self.pilots.leave("user0")
        self.pilots.leave("fake_user")
        yield d
        self.assertEqual(len(self.pilots.pilots), 1)

    @defer.inlineCallbacks
    def test_kick_user(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.pilots.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.pilots.port))
        responses.extend(expected_kick_responses(
            3, "user1", "192.168.1.3", self.pilots.port))
        responses.extend(expected_kick_responses(
            1, "user0", "192.168.1.2", self.pilots.port))

        d = self.expect_console_lines(responses)
        self.pilots.join("user0", "192.168.1.2")
        self.pilots.join("user1", "192.168.1.3")
        self.console_client.sendLine("kick user1")
        self.console_client.sendLine("kick user0")
        yield d
        self.assertEqual(len(self.pilots.pilots), 0)

    @defer.inlineCallbacks
    def test_kick_number(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.pilots.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.pilots.port))
        responses.extend(expected_join_responses(
            5, "user2", "192.168.1.4", self.pilots.port))
        responses.extend(expected_kick_responses(
            5, "user2", "192.168.1.4", self.pilots.port))
        responses.extend(expected_kick_responses(
            1, "user0", "192.168.1.2", self.pilots.port))

        d = self.expect_console_lines(responses)
        self.pilots.join("user0", "192.168.1.2")
        self.pilots.join("user1", "192.168.1.3")
        self.pilots.join("user2", "192.168.1.4")
        self.console_client.sendLine("kick 3")
        self.console_client.sendLine("kick 1")
        yield d
        self.assertEqual(len(self.pilots.pilots), 1)

    def test_kick_number_invalid(self):
        self.assertEqual(len(self.pilots.pilots), 0)
        self.console_client.sendLine("kick 1")
        self.assertEqual(len(self.pilots.pilots), 0)

    @defer.inlineCallbacks
    def test_show_common_info(self):
        d = self.expect_console_lines([
            " N       Name           Ping    Score   Army        Aircraft\\n",
        ])
        self.console_client.sendLine("user")
        yield d

        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.pilots.port)
        responses.extend([
            " N       Name           Ping    Score   Army        Aircraft\\n",
            " 1      user0            0       0      (0)None             \\n",
        ])
        d = self.expect_console_lines(responses)
        self.pilots.join("user0", "192.168.1.2")
        self.console_client.sendLine("user")
        yield d

        d = self.expect_console_lines([
            " N       Name           Ping    Score   Army        Aircraft\\n",
            " 1      user0            0       0      (0)None     * Red 1     A6M2-21\\n",
        ])
        self.pilots.spawn("user0")
        self.console_client.sendLine("user")
        yield d

    @defer.inlineCallbacks
    def test_show_statistics(self):
        d = self.expect_console_lines([
            "-------------------------------------------------------\\n",
        ])
        self.console_client.sendLine("user STAT")
        yield d

        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.pilots.port)
        responses.extend([
            "-------------------------------------------------------\\n",
            "Name: \\t\\tuser0\\n",
            "Score: \\t\\t0\\n",
            "State: \\t\\tIDLE\\n",
            "Enemy Aircraft Kill: \\t\\t0\\n",
            "Enemy Static Aircraft Kill: \\t\\t0\\n",
            "Enemy Tank Kill: \\t\\t0\\n",
            "Enemy Car Kill: \\t\\t0\\n",
            "Enemy Artillery Kill: \\t\\t0\\n",
            "Enemy AAA Kill: \\t\\t0\\n",
            "Enemy Wagon Kill: \\t\\t0\\n",
            "Enemy Ship Kill: \\t\\t0\\n",
            "Enemy Radio Kill: \\t\\t0\\n",
            "Friend Aircraft Kill: \\t\\t0\\n",
            "Friend Static Aircraft Kill: \\t\\t0\\n",
            "Friend Tank Kill: \\t\\t0\\n",
            "Friend Car Kill: \\t\\t0\\n",
            "Friend Artillery Kill: \\t\\t0\\n",
            "Friend AAA Kill: \\t\\t0\\n",
            "Friend Wagon Kill: \\t\\t0\\n",
            "Friend Ship Kill: \\t\\t0\\n",
            "Friend Radio Kill: \\t\\t0\\n",
            "Fire Bullets: \\t\\t0\\n",
            "Hit Bullets: \\t\\t0\\n",
            "Hit Air Bullets: \\t\\t0\\n",
            "Fire Roskets: \\t\\t0\\n",
            "Hit Roskets: \\t\\t0\\n",
            "Fire Bombs: \\t\\t0\\n",
            "Hit Bombs: \\t\\t0\\n",
            "-------------------------------------------------------\\n",
        ])
        d = self.expect_console_lines(responses)
        self.pilots.join("user0", "192.168.1.2")
        self.console_client.sendLine("user STAT")
        yield d


class MissionsTestCase(BaseTestCase):

    def test_no_mission(self):
        d = self.expect_console_lines([
            "Mission NOT loaded\\n",
        ])
        self.console_client.sendLine("mission")
        return d

    def test_load_mission(self):
        responses = expected_load_responses("net/dogfight/test.mis")
        responses.append(responses[-1])

        d = self.expect_console_lines(responses)
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission")
        return d

    def test_begin_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append(responses[-1])

        d = self.expect_console_lines(responses)
        self.console_client.sendLine("mission BEGIN")
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission BEGIN")
        self.console_client.sendLine("mission")
        return d

    def test_end_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append("Mission: net/dogfight/test.mis is Loaded\\n")

        d = self.expect_console_lines(responses)
        self.console_client.sendLine("mission END")
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission BEGIN")
        self.console_client.sendLine("mission END")
        self.console_client.sendLine("mission END END END")
        self.console_client.sendLine("mission")
        return d

    def test_destroy_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append("Mission NOT loaded\\n")

        d = self.expect_console_lines(responses)
        self.console_client.sendLine("mission DESTROY")
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission DESTROY")
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission BEGIN")
        self.console_client.sendLine("mission DESTROY")
        self.console_client.sendLine("mission")
        return d
