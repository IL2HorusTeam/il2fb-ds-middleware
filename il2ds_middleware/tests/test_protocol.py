# -*- coding: utf-8 -*-
from twisted.internet import error
from twisted.trial import unittest

from il2ds_middleware.parser import ConsolePassthroughParser
from il2ds_middleware.protocol import (ConsoleClient, ConsoleClientFactory,
    ReconnectingConsoleClientFactory, )

from il2ds_middleware.ds_emulator.protocol import ConsoleServerFactory


class ConsoleClientFactoryTestCase(unittest.TestCase):

    def test_connection(self):
        from twisted.internet import reactor
        server_listener = reactor.listenTCP(0, ConsoleServerFactory(),
                                            interface="127.0.0.1")

        def on_connected(client):
            self.assertIsInstance(client, ConsoleClient)

            d = client_factory.on_connection_lost
            server_listener.stopListening()
            client_connector.disconnect()
            return d

        parser = ConsolePassthroughParser()
        client_factory = ConsoleClientFactory(parser)
        d = client_factory.on_connecting.addCallback(on_connected)

        endpoint = server_listener.getHost()
        client_connector = reactor.connectTCP(endpoint.host, endpoint.port,
                                              client_factory)
        return d

    def test_connection_refused(self):
        parser = ConsolePassthroughParser()
        client_factory = ConsoleClientFactory(parser)
        d = client_factory.on_connecting

        from twisted.internet import reactor
        reactor.connectTCP("127.0.0.1", 20099, client_factory)

        return self.assertFailure(d, error.ConnectionRefusedError)

    def test_connection_lost(self):
        server_factory = ConsoleServerFactory()

        from twisted.internet import reactor
        server_listener = reactor.listenTCP(0, server_factory,
                                            interface="127.0.0.1")

        def on_connected(client):
            server_listener.stopListening()
            server_factory._client.transport.abortConnection()

        parser = ConsolePassthroughParser()
        client_factory = ConsoleClientFactory(parser)
        client_factory.on_connecting.addCallback(on_connected)
        d = client_factory.on_connection_lost

        endpoint = server_listener.getHost()
        reactor.connectTCP(endpoint.host, endpoint.port, client_factory)

        return self.assertFailure(d, error.ConnectionLost)

    def test_disconnection(self):
        server_factory = ConsoleServerFactory()

        from twisted.internet import reactor
        server_listener = reactor.listenTCP(0, server_factory,
                                            interface="127.0.0.1")

        def on_connected(client):
            server_listener.stopListening()
            client_connector.disconnect()

        parser = ConsolePassthroughParser()
        client_factory = ConsoleClientFactory(parser)
        client_factory.on_connecting.addCallback(on_connected)
        d = client_factory.on_connection_lost

        endpoint = server_listener.getHost()
        client_connector = reactor.connectTCP(endpoint.host, endpoint.port,
                                              client_factory)

        return d.addCallback(lambda result: self.assertIsNone(result))


class ReconnectingConsoleClientFactoryTestCase(unittest.TestCase):

    def test_connection(self):
        from twisted.internet import reactor
        server_listener = reactor.listenTCP(0, ConsoleServerFactory(),
                                            interface="127.0.0.1")

        def on_connected(client):
            self.assertIsInstance(client, ConsoleClient)

            d = client_factory.on_connection_lost
            server_listener.stopListening()
            client_factory.stopTrying()
            client_connector.disconnect()
            return d

        parser = ConsolePassthroughParser()
        client_factory = ReconnectingConsoleClientFactory(parser)
        d = client_factory.on_connecting.addCallback(on_connected)

        endpoint = server_listener.getHost()
        client_connector = reactor.connectTCP(endpoint.host, endpoint.port,
                                              client_factory)
        return d

    def test_connection_refused(self):
        parser = ConsolePassthroughParser()
        client_factory = ReconnectingConsoleClientFactory(parser)
        client_factory.stopTrying()
        d = client_factory.on_connecting

        from twisted.internet import reactor
        reactor.connectTCP("127.0.0.1", 20099, client_factory)

        return self.assertFailure(d, error.ConnectionRefusedError)

    def test_connection_lost(self):
        server_factory = ConsoleServerFactory()

        from twisted.internet import reactor
        server_listener = reactor.listenTCP(0, server_factory,
                                            interface="127.0.0.1")

        def on_connected1(client):
            server_factory._client.transport.abortConnection()

        def on_disconnected(failure):
            failure.trap(error.ConnectionLost)
            # Factory's deferreds will be already recreated here
            client_factory.on_connecting.addCallback(on_connected2)
            return client_factory.on_connection_lost.addCallback(
                lambda result: self.assertIsNone(result))

        def on_connected2(client):
            server_listener.stopListening()
            client_factory.stopTrying()
            client_connector.disconnect()

        parser = ConsolePassthroughParser()
        client_factory = ReconnectingConsoleClientFactory(parser)
        client_factory.on_connecting.addCallback(on_connected1)
        d = client_factory.on_connection_lost.addErrback(on_disconnected)

        endpoint = server_listener.getHost()
        client_connector = reactor.connectTCP(endpoint.host, endpoint.port,
                                              client_factory)
        return d

    def test_disconnection(self):
        server_factory = ConsoleServerFactory()

        from twisted.internet import reactor
        server_listener = reactor.listenTCP(0, server_factory,
                                            interface="127.0.0.1")

        def on_connected(client):
            server_listener.stopListening()
            client_factory.stopTrying()
            client_connector.disconnect()

        parser = ConsolePassthroughParser()
        client_factory = ReconnectingConsoleClientFactory(parser)
        client_factory.on_connecting.addCallback(on_connected)
        d = client_factory.on_connection_lost

        endpoint = server_listener.getHost()
        client_connector = reactor.connectTCP(endpoint.host, endpoint.port,
                                              client_factory)

        return d.addCallback(lambda result: self.assertIsNone(result))
