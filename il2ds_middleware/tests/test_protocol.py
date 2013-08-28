# -*- coding: utf-8 -*-

from twisted.internet import defer
from twisted.internet import error

from il2ds_middleware.tests.base import BaseTestCase


class ConsoleClientFactoryConnectionFailTestCase(BaseTestCase):

    console_server_port = 20000
    device_link_server_port = 10000

    def setUp(self):

        def on_connection_fail(err):
            if isinstance(err.value, error.ConnectionRefusedError):
                self.console_client_connector = None

        d = super(ConsoleClientFactoryConnectionFailTestCase, self).setUp()
        return d.addErrback(on_connection_fail)

    def test_connection_fail(self):
        self.assertNot(self.console_client_connector)

    @property
    def console_client_host_for_client(self):
        return self.console_server_host, self.console_server_port+1

    @property
    def device_link_host_for_client(self):
        return self.device_link_server_host, self.device_link_server_port+1


class ConsoleClientFactoryTestCase(BaseTestCase):

    def test_connection(self):
        self.assertTrue(self.console_client_connector)
