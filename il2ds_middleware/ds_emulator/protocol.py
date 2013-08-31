# -*- coding: utf-8 -*-

from twisted.internet.defer import Deferred
from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.python import log

from il2ds_middleware.protocol import DeviceLinkProtocol


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
        self.on_connected = Deferred()
        self.on_connection_lost = Deferred()

    def client_connected(self, client):
        if self.on_connected is not None:
            d, self.on_connected = self.on_connected, None
            d.callback(client)

    def client_left(self, client):
        if self.on_connection_lost is not None:
            d, self.on_connection_lost = self.on_connection_lost, None
            d.callback(client)


class DeviceLinkServerProtocol(DeviceLinkProtocol):

    receiver = None

    def requests_received(self, requests, address):
        if self.receiver is not None:
            self.receiver(requests, address, self)
