# -*- coding: utf-8 -*-
import tx_logging

from twisted.internet.defer import Deferred
from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver

from il2ds_middleware.constants import DEVICE_LINK_OPCODE as OPCODE
from il2ds_middleware.protocol import DeviceLinkProtocol
from il2ds_middleware.ds_emulator.constants import LONG_OPERATION_CMD


LOG = tx_logging.getLogger(__name__)


class ConsoleServer(LineReceiver):

    service = None

    def connectionMade(self):
        self.factory.client_connected(self)

    def connectionLost(self, reason):
        self.factory.client_left(self)

    def lineReceived(self, line):
        if self.service is not None:
            self.service.parse_line(line)

    def message(self, message):
        self.sendLine(message + '\\n')


class ConsoleServerFactory(ServerFactory):

    protocol = ConsoleServer

    def __init__(self):
        self._client = None
        self.on_connected = Deferred()
        self.on_connection_lost = Deferred()

    def buildProtocol(self, addr):
        self._client = ServerFactory.buildProtocol(self, addr)
        return self._client

    def client_connected(self, client):
        if self.on_connected is not None:
            d, self.on_connected = self.on_connected, None
            d.callback(client)

    def client_left(self, client):
        if self.on_connection_lost is not None:
            d, self.on_connection_lost = self.on_connection_lost, None
            d.callback(client)


class DeviceLinkServerProtocol(DeviceLinkProtocol):

    service = None

    def requests_received(self, requests, address):
        answers = []
        for request in requests:
            cmd, arg = request
            answer = None
            try:
                opcode = OPCODE.lookupByValue(cmd)
            except ValueError:
                if cmd == LONG_OPERATION_CMD:
                    return
                else:
                    LOG.error("Unknown command: {0}".format(cmd))
            else:
                if opcode == OPCODE.RADAR_REFRESH:
                    self.service.refresh_radar()
                elif opcode == OPCODE.PILOT_COUNT:
                    answer = self.service.pilot_count()
                elif opcode == OPCODE.PILOT_POS:
                    answer = self.service.pilot_pos(arg)
                elif opcode == OPCODE.STATIC_COUNT:
                    answer = self.service.static_count()
                elif opcode == OPCODE.STATIC_POS:
                    answer = self.service.static_pos(arg)
                if answer is not None:
                    answers.append(answer)
        if answers:
            self.send_answers(answers, address)
