# -*- coding: utf-8 -*-

from twisted.internet.protocol import DatagramProtocol, ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from zope.interface import implementer

from il2ds_middleware.ds_emulator.interfaces import ILineBroadcaster


class DeviceLinkProtocol(DatagramProtocol):

    service = None

    def datagramReceived(self, data, (host, port)):
        pass

    def answer(self, mesage, address):
        self.transport.write("A/" + mesage, address)

    def multi_answer(self, mesages, address):
        self.answer('/'.join(messages), address)


class ConsoleProtocol(LineReceiver):

    def connectionMade(self):
        self.factory.client_joined(self)

    def connectionLost(self, reason):
        self.factory.client_left(self)

    def lineReceived(self, line):
        self.factory.got_line(line)

    def message(self, message):
        self.sendLine(message + '\\n')


@implementer(ILineBroadcaster)
class ConsoleFactory(ServerFactory):

    protocol = ConsoleProtocol
    service = None

    def __init__(self):
        self.clients = []

    def client_joined(self, client):
        self.clients.append(client)

    def client_left(self, client):
        self.clients.remove(client)

    def got_line(self, line):
        if self.service:
            from twisted.internet import reactor
            reactor.callLater(0, self.service.parse_line, line)

    def broadcast_line(self, line):

        def do_broadcast(line):
            for client in self.clients:
                client.message(line)

        from twisted.internet import reactor
        reactor.callLater(0, do_broadcast, line)
