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

    def test_wrong_rid(self):
        self.console_client_factory._process_responce_id("rid|0")

    def test_malformed_rid(self):
        self.console_client_factory._process_responce_id("rid/smth")
        self.console_client_factory._process_responce_id("rid|smth")

    def test_mission_status(self):

        srvc = self.service.getServiceNamed('missions')

        def do_test():
            d = self.console_client_factory.mission_status()
            d.addCallback(check_not_loaded)
            d.addCallback(do_load)
            return d

        def do_load(_):
            srvc.load("net/dogfight/test.mis")
            d = self.console_client_factory.mission_status()
            d.addCallback(check_loaded)
            d.addCallback(do_begin)
            return d

        def do_begin(_):
            srvc.begin()
            d = self.console_client_factory.mission_status()
            d.addCallback(check_playing)
            return d

        def check_not_loaded(response):
            self.assertIsInstance(response, list)
            self.assertEqual(len(response), 1)
            self.assertEqual(response[0], "Mission NOT loaded")

        def check_loaded(response):
            self.assertIsInstance(response, list)
            self.assertEqual(len(response), 1)
            self.assertEqual(
                response[0], "Mission: net/dogfight/test.mis is Loaded")

        def check_playing(response):
            self.assertIsInstance(response, list)
            self.assertEqual(len(response), 1)
            self.assertEqual(
                response[0], "Mission: net/dogfight/test.mis is Playing")

        return do_test()

    def test_server_info(self):

        def callback(response):
            self.assertIsInstance(response, list)
            self.assertEqual(len(response), 3)
            self.assertEqual(response[0], "Type: Local server")
            self.assertEqual(response[1], "Name: Server")
            self.assertEqual(response[2], "Description: ")

        d = self.console_client_factory.server_info()
        return d.addCallback(callback)

    def test_long_operation(self):

        def callback(_):
            self.fail()

        def errback(err):
            self.assertIsInstance(err.value, defer.TimeoutError)

        d = self.console_client_factory._send_request("horus long operation")
        return d.addCallbacks(callback, errback)
