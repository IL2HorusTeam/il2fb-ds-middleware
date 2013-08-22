# -*- coding: utf-8 -*-

from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory, DatagramProtocol
from twisted.protocols.basic import LineReceiver

from il2ds_middleware.device_link import OPCODE
from il2ds_middleware.ds_emulator.protocol import (ConsoleFactory,
    ConsoleProtocol, )


class ConsoleServerFactory(ConsoleFactory):

    def __init__(self):
        ConsoleFactory.__init__(self)
        self.on_connection_lost = Deferred()

    def client_left(self, client):
        ConsoleFactory.client_left(self, client)
        self.on_connection_lost.callback(client)


class ConsoleClientProtocol(LineReceiver):

    def connectionMade(self):
        self.factory.client_joined(self)

    def connectionLost(self, reason):
        self.factory.client_left(self)

    def lineReceived(self, line):
        if self.factory.receiver:
            self.factory.receiver(line)


class ConsoleClientFactory(ClientFactory):

    protocol = ConsoleClientProtocol

    def __init__(self):
        self.clients = []
        self.on_connection_made = Deferred()
        self.on_connection_lost = Deferred()

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


class DeviceLinkClientProtocol(DatagramProtocol):

    receiver = None

    def __init__(self, address):
        self.host, self.port = address

    def startProtocol(self):
        self.transport.connect(self.host, self.port)

    def datagramReceived(self, data, (host, port)):
        if self.receiver:
            self.receiver(data)

    def request(self, message):
        self.transport.write("R/" + message)

    def multi_request(self, mesages):
        self.request('/'.join(messages))

    def radar_refresh(self):
        self.request(OPCODE.RADAR_REFRESH.value)

    def pilot_count(self):
        self.request(OPCODE.PILOT_COUNT.value)
