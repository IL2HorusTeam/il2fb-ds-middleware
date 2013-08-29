# -*- coding: utf-8 -*-

from twisted.internet import defer
from twisted.trial.unittest import TestCase

from il2ds_middleware.protocol import ConsoleClientFactory

from il2ds_middleware.ds_emulator.service import RootService as DSService
from il2ds_middleware.ds_emulator.protocol import (ConsoleServerFactory,
    DeviceLinkServerProtocol, )


class BaseTestCase(TestCase):

    console_server_host = "127.0.0.1"
    console_server_port = 0
    device_link_server_host = "127.0.0.1"
    device_link_server_port = 0
    timeout_value = 0.05

    def setUp(self):
        self._listen_server()
        return self._connect_client()

    def _listen_server(self):
        self.console_server_factory = ConsoleServerFactory()
        self.service = DSService(self.console_server_factory)
        self.dl_server = DeviceLinkServerProtocol()

        self.console_server_factory.receiver = self.service.parse_line
        self.dl_server.on_requests = self.service.getServiceNamed(
            'dl').got_requests

        from twisted.internet import reactor
        # Start console server
        self.console_server_listener = reactor.listenTCP(
            self.console_server_port, self.console_server_factory,
            interface=self.console_server_host)
        # Start Device Link server
        self.dl_server_listener = reactor.listenUDP(
            self.device_link_server_port, self.dl_server,
            interface=self.device_link_server_host)
        self.service.startService()

    def _connect_client(self):
        self.console_client_factory = ConsoleClientFactory()

        # self.dl_client = DeviceLinkClientProtocol(
        #     self.device_link_host_for_client)

        from twisted.internet import reactor
        host, port = self.console_client_host_for_client
        self.console_client_connector = reactor.connectTCP(
            host, port, self.console_client_factory)
        # self.dl_client_port = reactor.listenUDP(0, self.dl_client)
        return self.console_client_factory.on_connecting

    def tearDown(self):
        self.console_server_factory.on_data = None
        self.dl_server.on_request = None
        self.console_client_factory.receiver = None
        # self.dl_client.receiver = None

        console_server_stopped = defer.maybeDeferred(
            self.console_server_listener.stopListening)
        dl_server_stopped = defer.maybeDeferred(
            self.dl_server_listener.stopListening)
        # dl_client_stopped = defer.maybeDeferred(
        #     self.dl_client_port.stopListening)

        dlist = [
            console_server_stopped, dl_server_stopped,
            # dl_client_stopped,
            self.service.stopService(), ]
        if self.console_client_connector is not None:
            dlist.extend([
                self.console_client_factory.on_connection_lost,
                self.console_server_factory.on_connection_lost, ])
            self.console_client_connector.disconnect()
        return defer.gatherResults(dlist)

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

    def _make_timeout(self, callback):
        from twisted.internet import reactor
        return reactor.callLater(self.timeout_value, callback, None)

    def _set_console_expecting_receiver(self, expected_lines, d):
        self.console_client_factory.got_line = \
            self._get_expecting_line_receiver(expected_lines, d)

    @property
    def console_client_host_for_client(self):
        if self.console_server_listener is None:
            return (None, None)
        endpoint = self.console_server_listener.getHost()
        return endpoint.host, endpoint.port

    @property
    def device_link_host_for_client(self):
        if self.dl_server_listener is None:
            return (None, None)
        endpoint = self.dl_server_listener.getHost()
        return endpoint.host, endpoint.port
