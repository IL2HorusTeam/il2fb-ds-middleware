# -*- coding: utf-8 -*-

from twisted.internet.defer import Deferred
from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.python import log

from zope.interface import implementer

from il2ds_middleware.protocol import DeviceLinkProtocol
from il2ds_middleware.ds_emulator.interfaces import ILineBroadcaster

class DeviceLinkServerProtocol(DeviceLinkProtocol):

    on_requests = None

    def requests_received(self, requests, address):
        if self.on_requests is not None:
            self.on_requests(requests, address, self)


class ConsoleServerProtocol(LineReceiver):

    def connectionMade(self):
        self.factory.client_joined(self)

    def connectionLost(self, reason):
        self.factory.client_left(self)

    def lineReceived(self, line):
        self.factory.got_line(line)

    def message(self, message):
        self.sendLine(message + '\\n')


@implementer(ILineBroadcaster)
class ConsoleServerFactory(ServerFactory):

    protocol = ConsoleServerProtocol
    receiver = None

    def __init__(self):
        self.clients = []
        self.on_connection_lost = Deferred()

    def client_joined(self, client):
        self.clients.append(client)

    def client_left(self, client):
        self.clients.remove(client)
        if self.on_connection_lost is not None:
            d, self.on_connection_lost = self.on_connection_lost, None
            d.callback(client)

    def got_line(self, line):
        if self.receiver is not None:
            self.receiver(line)

    def broadcast_line(self, line):

        def do_broadcast(line):
            for client in self.clients:
                client.message(line)

        from twisted.internet import reactor
        reactor.callLater(0, do_broadcast, line)
