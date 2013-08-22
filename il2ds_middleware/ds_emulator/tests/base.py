# -*- coding: utf-8 -*-

from twisted.internet import defer
from twisted.trial.unittest import TestCase

from il2ds_middleware.ds_emulator.service import RootService
from il2ds_middleware.ds_emulator.protocol import DeviceLinkProtocol
from il2ds_middleware.ds_emulator.tests.protocol import (ConsoleServerFactory,
    ConsoleClientFactory, ConsoleClientProtocol, DeviceLinkClientProtocol, )


class BaseTestCase(TestCase):

    def setUp(self):
        self._listen_server()
        return self._connect_client()

    def _listen_server(self):
        self.sfactory = ConsoleServerFactory()
        self.sservice = RootService(self.sfactory)
        self.sfactory.service = self.sservice
        self.sservice.startService()

        self.dl_server = DeviceLinkProtocol()

        from twisted.internet import reactor
        self.console_server_port = reactor.listenTCP(
            0, self.sfactory, interface="127.0.0.1")
        self.dl_server_port = reactor.listenUDP(
            0, self.dl_server, interface="127.0.0.1")

    def _connect_client(self):
        self.cfactory = ConsoleClientFactory()

        ds_host = self.dl_server_port.getHost()
        self.dl_client = DeviceLinkClientProtocol((ds_host.host, ds_host.port))

        from twisted.internet import reactor
        self.console_client_port = reactor.connectTCP(
            "127.0.0.1", self.console_server_port.getHost().port,
            self.cfactory)
        self.dl_client_port = reactor.listenUDP(0, self.dl_client)

        return self.cfactory.on_connection_made

    def tearDown(self):
        self.cfactory.receiver = None
        self.dl_client.receiver = None

        console_server_stopped = defer.maybeDeferred(
            self.console_server_port.stopListening)
        dl_server_stopped = defer.maybeDeferred(
            self.dl_server_port.stopListening)
        dl_client_stopped = defer.maybeDeferred(
            self.dl_client_port.stopListening)

        self.console_client_port.disconnect()

        return defer.gatherResults([
            console_server_stopped, dl_server_stopped, dl_client_stopped,
            self.cfactory.on_connection_lost, self.sfactory.on_connection_lost,
            self.sservice.stopService(), ])

    def _make_timeout(self, callback):
        from twisted.internet import reactor
        return reactor.callLater(0.1, callback, None)

    def _get_unexpecting_line_receiver(self, d):

        def got_line(line):
            timeout.cancel()
            from twisted.trial.unittest import FailTest
            d.errback(FailTest("Unexpected data:\n\t{0}.".format(line)))

        timeout = self._make_timeout(d.callback)
        return got_line

    def _get_expecting_line_receiver(self, expected_lines, d):

        def got_line(line):
            try:
                self.assertEqual(line, expected_lines.pop(0))
            except Exception as e:
                timeout.cancel()
                d.errback(e)
            else:
                if expected_lines:
                    return
                timeout.cancel()
                d.callback(None)

        def on_timeout(_):
            from twisted.trial.unittest import FailTest
            d.errback(FailTest(
                'Timed out, remaining lines:\n\t'+'\n\t'.join(expected_lines)))

        timeout = self._make_timeout(on_timeout)
        return got_line
