# -*- coding: utf-8 -*-
from twisted.protocols import basic, loopback
from twisted.trial import unittest

from il2ds_middleware.protocol import DeviceLinkProtocol

from il2ds_middleware.ds_emulator.protocol import (ConsoleServer,
    ConsoleServerFactory, DeviceLinkServerProtocol, )
from il2ds_middleware.ds_emulator.service import RootService

from il2ds_middleware.tests import expect_lines


class DeviceLinkClient(DeviceLinkProtocol):

    def answers_received(self, answers, address):
        line = "A/" + self.compose(answers)
        self.got_line(line)

    def got_line(self, line):
        pass


class BaseTestCase(unittest.TestCase):

    log_path = None

    def setUp(self):
        # Init console --------------------------------------------------------
        self.console_client = basic.LineReceiver()
        self.console_client.lineReceived = lambda line: None

        factory = ConsoleServerFactory()
        self.console_server = factory.buildProtocol(addr=None)

        self.server_service = RootService(self.log_path)

        self.server_service.client = self.console_server
        self.console_server.service = self.server_service

        self.server_service.startService()

        loopback.loopbackAsync(self.console_server, self.console_client)

        # Init Device Link ----------------------------------------------------
        self.dl_server = DeviceLinkServerProtocol()
        self.dl_server.service = self.server_service.getServiceNamed('dl')

        from twisted.internet import reactor
        self.dl_server_listener = reactor.listenUDP(0, self.dl_server,
                                                    interface="127.0.0.1")

        endpoint = self.dl_server_listener.getHost()
        self.dl_client = DeviceLinkClient((endpoint.host, endpoint.port))
        self.dl_client_connector = reactor.listenUDP(0, self.dl_client)

    def tearDown(self):
        self.dl_client_connector.stopListening()
        self.dl_server_listener.stopListening()

        self.console_server.transport.loseConnection()
        return self.server_service.stopService()

    def expect_console_lines(self, expected_lines=None, timeout=None):
        self.console_client.lineReceived, d = expect_lines(expected_lines,
                                                           timeout)
        return d

    def expect_dl_lines(self, expected_lines=None, timeout=None):
        self.dl_client.got_line, d = expect_lines(expected_lines, timeout)
        return d
