# -*- coding: utf-8 -*-

from twisted.internet import defer
from twisted.internet.protocol import DatagramProtocol
from twisted.python.constants import ValueConstant, Values
from twisted.trial.unittest import FailTest, TestCase

from il2ds_middleware.ds_emulator.protocol import DeviceLinkProtocol
from il2ds_middleware.ds_emulator.tests.helpers import (
    LineReceiverTestCaseMixin, )


class OPCODE(Values):

    """
    Constants representing operation codes for DeviceLink interface.
    """

    RADAR_REFRESH = ValueConstant("1001")


class ClientProtocol(DatagramProtocol):

    receiver = None

    def __init__(self, address):
        self.host, self.port = address

    def startProtocol(self):
        self.transport.connect(self.host, self.port)

    def datagramReceived(self, data, (host, port)):
        if self.receiver:
            self.receiver(data, (host, port))

    def request(self, message):
        self.transport.write("R/" + message)

    def multi_answer(self, mesages):
        self.answer('/'.join(messages))

    def radar_refresh(self):
        self.request(OPCODE.RADAR_REFRESH.value)


class DeviceLinkTestCase(TestCase, LineReceiverTestCaseMixin):

    def setUp(self):
        self.server_port = self._listen_server()
        self.client_port = self._connect_client()

    def _listen_server(self):
        self.server = DeviceLinkProtocol()
        from twisted.internet import reactor
        return reactor.listenUDP(0, self.server, interface="127.0.0.1")

    def _connect_client(self):
        server_host = self.server_port.getHost()
        self.client = ClientProtocol((server_host.host, server_host.port))
        from twisted.internet import reactor
        return reactor.listenUDP(0, self.client)

    def tearDown(self):
        server_stopped = defer.maybeDeferred(self.server_port.stopListening)
        client_stopped = defer.maybeDeferred(self.client_port.stopListening)
        return defer.gatherResults([
            server_stopped, client_stopped])

    def test_radar_refresh(self):
        d = defer.Deferred()
        self.client.receiver = self._get_unexpecting_line_receiver(d)
        self.client.radar_refresh()
        return d
