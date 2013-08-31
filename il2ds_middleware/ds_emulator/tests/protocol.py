# -*- coding: utf-8 -*-

from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver

from il2ds_middleware.protocol import DeviceLinkProtocol


class ConsoleClient(LineReceiver):

    def connectionMade(self):
        self.factory.client_joined(self)

    def connectionLost(self, reason):
        self.factory.client_left(self)

    def lineReceived(self, line):
        self.got_line(line)

    def got_line(self, line):
        if self.factory.receiver is not None:
            self.factory.receiver(line)


class ConsoleClientFactory(ClientFactory):

    protocol = ConsoleClient
    receiver = None

    def __init__(self):
        self.clients = []
        self.on_connecting = Deferred()
        self.on_connection_lost = Deferred()

    def client_joined(self, client):
        if self.on_connecting:
            d, self.on_connecting = self.on_connecting, None
            d.callback(client)
        self.clients.append(client)

    def client_left(self, client):
        if self.on_connection_lost:
            d, self.on_connection_lost = self.on_connection_lost, None
            d.callback(client)
        self.clients.remove(client)


class DeviceLinkClient(DeviceLinkProtocol):

    receiver = None

    def answers_received(self, answers, address):
        if self.receiver is not None:
            line = "A/" + self._format(answers)
            self.receiver(line)
