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
        d = self.expect_console_lines(["foo\\n"])
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
