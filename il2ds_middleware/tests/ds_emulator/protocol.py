# -*- coding: utf-8 -*-

from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from zope.interface import implementer

from il2ds_middleware.tests.ds_emulator.interfaces import ILineBroadcaster

class DSConsoleProtocol(LineReceiver):

    def connectionMade(self):
        self.factory.client_joined(self)

    def connectionLost(self, reason):
        self.factory.client_left(self)

    def lineReceived(self, line):
        self.factory.got_line(line)

    def message(self, message):
        self.transport.write(message + '\\n')


@implementer(ILineBroadcaster)
class DSConsoleFactory(ServerFactory):

    protocol = DSConsoleProtocol

    def __init__(self, service):
        self.clients = []
        self.service = service

    def client_joined(self, client):
        self.clients.append(client)

    def client_left(self, client):
        self.clients.remove(client)

    def got_line(self, line):
        self.service.parse_line(line)

    def broadcast_line(self, line):
        for client in self.clients:
            client.message(line)
