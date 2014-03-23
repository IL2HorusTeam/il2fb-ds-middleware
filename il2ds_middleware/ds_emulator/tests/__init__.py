# -*- coding: utf-8 -*-
from twisted.internet import defer
from twisted.protocols import basic, loopback
from twisted.python.failure import Failure
from twisted.trial import unittest

from il2ds_middleware.protocol import DeviceLinkProtocol

from il2ds_middleware.ds_emulator.protocol import (ConsoleServer,
    ConsoleServerFactory, DeviceLinkServerProtocol, )
from il2ds_middleware.ds_emulator.service import RootService


def add_watchdog(deferred, timeout=None, callback=None):

    def _callback(value):
        if not watchdog.called:
            watchdog.cancel()
        return value

    deferred.addBoth(_callback)

    def on_timeout():
        if deferred.called:
            return
        if callback is not None:
            callback()
        else:
            defer.timeout(deferred)

    from twisted.internet import reactor
    watchdog = reactor.callLater(timeout or 0.05, on_timeout)


class DeviceLinkClient(DeviceLinkProtocol):

    def answers_received(self, answers, address):
        line = "A/" + self.compose(answers)
        self.got_line(line)

    def got_line(self, line):
        pass


class UnexpectedLineError(Exception):

    def __init__(self, line):
        self.line = line

    def __str__(self):
        return "Unexpected line: {0}".format(self.line)


class BaseTestCase(unittest.TestCase):

    device_link_server_host = "127.0.0.1"
    device_link_server_port = 0

    def setUp(self):
        # Init console --------------------------------------------------------
        self.console_client = basic.LineReceiver()
        self.console_client.lineReceived = lambda line: None

        self.console_server = ConsoleServer()
        self.console_server.factory = ConsoleServerFactory()

        self.server_service = RootService()

        self.server_service.client = self.console_server
        self.console_server.service = self.server_service

        self.server_service.startService()

        loopback.loopbackAsync(self.console_server, self.console_client)

        # Init Device Link ----------------------------------------------------
        self.dl_server = DeviceLinkServerProtocol()
        self.dl_server.service = self.server_service.getServiceNamed('dl')

        from twisted.internet import reactor
        self.dl_server_listener = reactor.listenUDP(
            self.device_link_server_port, self.dl_server,
            interface=self.device_link_server_host)

        endpoint = self.dl_server_listener.getHost()
        self.dl_client = DeviceLinkClient((endpoint.host, endpoint.port))
        self.dl_client_connector = reactor.listenUDP(0, self.dl_client)

    def tearDown(self):
        self.dl_client_connector.stopListening()
        self.dl_server_listener.stopListening()

        self.console_server.transport.loseConnection()
        return self.server_service.stopService()

    def _get_expecting_line_receiver(self, expected_lines, timeout=None):
        expected_lines = expected_lines[:]

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
                "Timed out, remaining lines:\n{0}".format(
                "\n\t".join(["\"%s\"" % line for line in expected_lines]))))

        d = defer.Deferred()
        add_watchdog(d, timeout, on_timeout)
        return got_line, d

    def _get_unexpecting_line_receiver(self, timeout=None):

        def got_line(line):
            d.errback(Failure(UnexpectedLineError(line)))

        def errback(failure):
            failure.trap(defer.TimeoutError)

        d = defer.Deferred().addErrback(errback)
        add_watchdog(d, timeout)
        return got_line, d

    def expect_console_lines(self, expected_lines=None, timeout=None):
        self.console_client.lineReceived, d = \
            self._get_expecting_line_receiver(expected_lines, timeout) \
            if expected_lines else \
            self._get_unexpecting_line_receiver(timeout)
        return d

    def expect_dl_lines(self, expected_lines=None, timeout=None):
        self.dl_client.got_line, d = \
            self._get_expecting_line_receiver(expected_lines, timeout) \
            if expected_lines else \
            self._get_unexpecting_line_receiver(timeout)
        return d
