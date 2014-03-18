# -*- coding: utf-8 -*-
from twisted.internet import defer
from twisted.internet.error import ConnectionRefusedError

from il2ds_middleware.constants import DeviceLinkCommand
from il2ds_middleware.parser import DeviceLinkParser
from il2ds_middleware.tests.base import BaseMiddlewareTestCase
from il2ds_middleware.ds_emulator.constants import LONG_OPERATION_CMD


class ConsoleClientFactoryConnectionFailTestCase(BaseMiddlewareTestCase):

    console_server_port = 20099
    device_link_server_port = 10099

    def setUp(self):

        def on_connection_fail(failure):
            failure.trap(ConnectionRefusedError)
            self.console_client_connector = None

        d = super(ConsoleClientFactoryConnectionFailTestCase, self).setUp()
        return d.addErrback(on_connection_fail)

    def test_connection_fail(self):
        self.assertNot(self.console_client_connector)

    @property
    def console_client_address_for_client(self):
        """
        Redefine base property to return wrong server console address.
        """
        return self.console_server_host, self.console_server_port + 1

    @property
    def device_link_address_for_client(self):
        """
        Redefine base property to return wrong server Device Link address.
        """
        return self.device_link_server_host, self.device_link_server_port + 1


class ConsoleClientFactoryTestCase(BaseMiddlewareTestCase):

    def test_connection(self):
        self.assertTrue(self.console_client_connector)

    def test_wrong_rid(self):
        self.console_client._process_request_wrapper("rid|0")

    def test_malformed_rid(self):
        self.console_client._process_request_wrapper("rid/smth")
        self.console_client._process_request_wrapper("rid|smth")

    @defer.inlineCallbacks
    def test_mission_status(self):
        srvc = self.service.getServiceNamed('missions')

        response = yield self.console_client.mission_status()
        self.assertIsInstance(response, list)
        self.assertEqual(response, ["Mission NOT loaded", ])

        srvc.load("net/dogfight/test.mis")
        response = yield self.console_client.mission_status()
        self.assertIsInstance(response, list)
        self.assertEqual(
            response, ["Mission: net/dogfight/test.mis is Loaded", ])

        srvc.begin()
        response = yield self.console_client.mission_status()

        self.assertIsInstance(response, list)
        self.assertEqual(
            response, ["Mission: net/dogfight/test.mis is Playing", ])

    @defer.inlineCallbacks
    def test_server_info(self):
        response = yield self.console_client.server_info()
        self.assertIsInstance(response, list)
        self.assertEqual(response, [
            "Type: Local server",
            "Name: Server",
            "Description: ",
        ])

    def test_long_operation(self):
        d = self.console_client._send_request(LONG_OPERATION_CMD)
        return self.assertFailure(d, defer.TimeoutError)

    @defer.inlineCallbacks
    def test_manual_input(self):
        d = self.expect_console_lines([
            "mission",
            "Mission NOT loaded",
        ])
        self.service.manual_input("mission")
        yield d

        # Wait to receive <consoleN><1>
        d = defer.Deferred()
        from twisted.internet import reactor
        reactor.callLater(0.05, d.callback, None)
        yield d

    @defer.inlineCallbacks
    def test_mission_load(self):
        response = yield self.console_client.mission_load(
            "net/dogfight/test.mis")

        self.assertIsInstance(response, list)
        obligatory_responses = [
            "Loading mission net/dogfight/test.mis...",
            "Load bridges",
            "Load static objects",
            "Mission: net/dogfight/test.mis is Loaded",
        ]

        for obligatory_response in obligatory_responses:
            self.assertEqual(response.count(obligatory_response), 1)

    @defer.inlineCallbacks
    def test_mission_begin(self):
        yield self.console_client.mission_load("net/dogfight/test.mis")
        response = yield self.console_client.mission_begin()

        self.assertIsInstance(response, list)
        self.assertEqual(response, [
            "Mission: net/dogfight/test.mis is Playing",
        ])

    @defer.inlineCallbacks
    def test_mission_end(self):
        yield self.console_client.mission_load("net/dogfight/test.mis")
        yield self.console_client.mission_begin()
        response = yield self.console_client.mission_end()

        self.assertIsInstance(response, list)
        self.assertEqual(response, [
            "Mission: net/dogfight/test.mis is Loaded",
        ])

    @defer.inlineCallbacks
    def test_mission_destroy(self):
        yield self.console_client.mission_load("net/dogfight/test.mis")
        yield self.console_client.mission_begin()
        response = yield self.console_client.mission_destroy()

        self.assertIsInstance(response, list)
        self.assertEqual(response, ["Mission NOT loaded", ])

    def test_chat(self):
        responses = ["Chat: Server: \ttest message"]*3
        responses.append("Command not found: chat test message")

        d = self.expect_console_lines(responses)
        self.console_client.chat_all("test message")
        self.console_client.chat_user("test message", "user0")
        self.console_client.chat_army("test message", "0")
        self.console_client.sendLine("chat test message")
        return d


class DeviceLinkClientProtocolBaseTestCase(BaseMiddlewareTestCase):

    def setUp(self):
        d = BaseMiddlewareTestCase.setUp(self)
        self.pilots = self.service.getServiceNamed('pilots')
        self.static = self.service.getServiceNamed('static')
        return d

    def _spawn_pilots(self):
        for i in xrange(2, 255):
            callsign = "user{0}".format(i-2)
            self.pilots.join(callsign, "192.168.1.{0}".format(i))
            self.pilots.spawn(callsign, pos={
                'x': i*100, 'y': i*200, 'z': i*300, })

    def _spawn_static(self):
        for i in xrange(1000):
            self.static.spawn("{0}_Static".format(i), pos={
                'x': i*100, 'y': i*200, 'z': i*300, })


class DeviceLinkClientProtocolTestCase(DeviceLinkClientProtocolBaseTestCase):

    timeout = 0.2

    def test_long_operation(self):
        command = DeviceLinkCommand(LONG_OPERATION_CMD, None)
        d = self.dl_client._deferred_request(command)
        return self.assertFailure(d, defer.TimeoutError)

    @defer.inlineCallbacks
    def test_pilot_count(self):
        response = yield self.dl_client.pilot_count()
        self.assertEqual(response, '0')

        self._spawn_pilots()
        yield self.dl_client.refresh_radar()

        response = yield self.dl_client.pilot_count()
        self.assertEqual(response, '253')

    @defer.inlineCallbacks
    def test_pilot_pos(self):
        self.pilots.join("user0", "192.168.1.{0}")
        self.pilots.spawn("user0", pos={'x': 100, 'y': 200, 'z': 300, })

        yield self.dl_client.refresh_radar()
        response = yield self.dl_client.pilot_pos(0)
        self.assertEqual(response, '0:user0_0;100;200;300')

    @defer.inlineCallbacks
    def test_all_pilots_pos(self):
        self._spawn_pilots()
        yield self.dl_client.refresh_radar()
        responses = yield self.dl_client.all_pilots_pos()

        self.assertIsInstance(responses, list)
        self.assertEqual(len(responses), 253)
        checked = []
        for s in responses:
            start = s.index('user') + 4
            stop = s.index(';')

            idx = int(s[start:stop].split('_')[0])
            self.assertNotIn(idx, checked)
            checked.append(idx)

    @defer.inlineCallbacks
    def test_static_count(self):
        response = yield self.dl_client.static_count()
        self.assertEqual(response, '0')

        self._spawn_static()
        yield self.dl_client.refresh_radar()
        response = yield self.dl_client.static_count()
        self.assertEqual(response, '1000')

    @defer.inlineCallbacks
    def test_static_pos(self):
        self.static.spawn("0_Static", pos={'x': 100, 'y': 200, 'z': 300, })
        yield self.dl_client.refresh_radar()
        response = yield self.dl_client.static_pos(0)
        self.assertEqual(response, '0:0_Static;100;200;300')

    @defer.inlineCallbacks
    def test_all_static_pos(self):
        self._spawn_static()

        yield self.dl_client.refresh_radar()
        responses = yield self.dl_client.all_static_pos()

        self.assertIsInstance(responses, list)
        self.assertEqual(len(responses), 1000)
        checked = []
        for s in responses:
            start = s.index(':') + 1
            stop = s.index('_')
            idx = int(s[start:stop])
            self.assertNotIn(idx, checked)
            checked.append(idx)

    @defer.inlineCallbacks
    def test_all_pos_with_no_count(self):
        response = yield self.dl_client._all_pos(
            lambda: defer.succeed(0), 'foo')
        self.assertIsInstance(response, list)
        self.assertEqual(response, [])


class PasredDeviceLinkClientProtocolTestCase(
    DeviceLinkClientProtocolBaseTestCase):

    dl_client_parser_class = DeviceLinkParser
    timeout = 0.2

    @defer.inlineCallbacks
    def test_pilot_count(self):
        response = yield self.dl_client.pilot_count()
        self.assertEqual(response, 0)

        self._spawn_pilots()
        yield self.dl_client.refresh_radar()
        response = yield self.dl_client.pilot_count()
        self.assertEqual(response, 253)

    @defer.inlineCallbacks
    def test_pilot_pos(self):
        self.pilots.join("user0", "192.168.1.{0}")
        self.pilots.spawn("user0", pos={'x': 100, 'y': 200, 'z': 300, })

        yield self.dl_client.refresh_radar()
        response = yield self.dl_client.pilot_pos(0)

        self.assertIsInstance(response, dict)
        self.assertEqual(response, {
            'id': 0,
            'callsign': "user0",
            'pos': {
                'x': 100,
                'y': 200,
                'z': 300,
            },
        })

    @defer.inlineCallbacks
    def test_all_pilots_pos(self):
        self._spawn_pilots()
        yield self.dl_client.refresh_radar()
        responses = yield self.dl_client.all_pilots_pos()

        self.assertIsInstance(responses, list)
        self.assertEqual(len(responses), 253)
        checked = []
        for response in responses:
            self.assertIsInstance(response, dict)
            idx = response['id']
            self.assertNotIn(idx, checked)
            checked.append(idx)

    @defer.inlineCallbacks
    def test_static_count(self):
        response = yield self.dl_client.static_count()
        self.assertEqual(response, 0)

        self._spawn_static()
        yield self.dl_client.refresh_radar()

        response = yield self.dl_client.static_count()
        self.assertEqual(response, 1000)

    @defer.inlineCallbacks
    def test_static_pos(self):
        self.static.spawn("0_Static", pos={'x': 100, 'y': 200, 'z': 300, })
        yield self.dl_client.refresh_radar()
        response = yield self.dl_client.static_pos(0)

        self.assertIsInstance(response, dict)
        self.assertEqual(response, {
            'id': 0,
            'name': "0_Static",
            'pos': {
                'x': 100,
                'y': 200,
                'z': 300,
            },
        })

    @defer.inlineCallbacks
    def test_all_static_pos(self):
        self._spawn_static()
        yield self.dl_client.refresh_radar()
        responses = yield self.dl_client.all_static_pos()

        self.assertIsInstance(responses, list)
        self.assertEqual(len(responses), 1000)
        checked = []
        for response in responses:
            self.assertIsInstance(response, dict)
            idx = response['id']
            self.assertNotIn(idx, checked)
            checked.append(idx)
