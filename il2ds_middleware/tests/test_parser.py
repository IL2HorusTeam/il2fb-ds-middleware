# -*- coding: utf-8 -*-

from twisted.trial.unittest import TestCase

from il2ds_middleware.constants import MISSION_STATUS, PILOT_LEAVE_REASON
from il2ds_middleware.parser import ConsoleParser, DeviceLinkParser
from il2ds_middleware.tests.service import PilotService


class ConsoleParserTestCase(TestCase):

    def setUp(self):
        self.pilot_srvc = PilotService()
        self.parser = ConsoleParser(self.pilot_srvc)
        self.pilot_srvc.startService()

    def tearDown(self):
        return self.pilot_srvc.stopService()

    def test_server_info(self):
        datas = [
            "Type: Local server",
            "Name: Test server",
            "Description: Horus test server", ]
        result = self.parser.server_info(datas)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('type'), "Local server")
        self.assertEqual(result.get('name'), "Test server")
        self.assertEqual(result.get('description'), "Horus test server")

    def test_mission_status(self):
        status, mission = self.parser.mission_status([
            "Mission NOT loaded", ])
        self.assertEqual(status, MISSION_STATUS.NOT_LOADED)
        self.assertEqual(mission, None)

        status, mission = self.parser.mission_status([
            "Mission: net/dogfight/test.mis is Loaded", ])
        self.assertEqual(status, MISSION_STATUS.LOADED)
        self.assertEqual(mission, "net/dogfight/test.mis")

        status, mission = self.parser.mission_status([
            "Mission: net/dogfight/test.mis is Playing", ])
        self.assertEqual(status, MISSION_STATUS.PLAYING)
        self.assertEqual(mission, "net/dogfight/test.mis")

        datas = ["some fake data", ]
        result = self.parser.mission_status(datas)
        self.assertIsInstance(result, list)
        self.assertEqual(len(datas), len(result))
        self.assertEqual(datas[0], result[0])

    def test_mission_load(self):
        datas = [
            "Loading mission net/dogfight/test.mis...",
            "Load bridges",
            "Load static objects",
            "##### House without collision (3do/Tree/Tree2.sim)",
            "##### House without collision "
                "(3do/Buildings/Port/Floor/live.sim)",
            "##### House without collision "
                "(3do/Buildings/Port/BaseSegment/live.sim)",
            "Mission: net/dogfight/test.mis is Loaded", ]
        status, mission = self.parser.mission_load(datas)
        self.assertEqual(status, MISSION_STATUS.LOADED)
        self.assertEqual(mission, "net/dogfight/test.mis")

    def test_mission_begin(self):
        status, mission = self.parser.mission_begin([
            "Mission: net/dogfight/test.mis is Playing", ])
        self.assertEqual(status, MISSION_STATUS.PLAYING)
        self.assertEqual(mission, "net/dogfight/test.mis")

    def test_mission_end(self):
        status, mission = self.parser.mission_end([
            "Mission: net/dogfight/test.mis is Loaded", ])
        self.assertEqual(status, MISSION_STATUS.LOADED)
        self.assertEqual(mission, "net/dogfight/test.mis")

    def test_mission_destroy(self):
        status, mission = self.parser.mission_destroy([
            "Mission NOT loaded", ])
        self.assertEqual(status, MISSION_STATUS.NOT_LOADED)
        self.assertEqual(mission, None)

    def test_user_joined(self):

        def on_user_join(info):
            self.assertIsInstance(info, dict)
            self.assertEqual(info.get('channel'), 0)
            self.assertEqual(info.get('ip'), "192.168.1.2")
            self.assertEqual(info.get('callsign'), "user0")

        self.pilot_srvc.receiver = on_user_join
        self.parser.parse_line(
            "socket channel '0' start creating: ip 192.168.1.2:21000")
        self.parser.parse_line("Chat: --- user0 joins the game.")
        self.parser.parse_line(
            "socket channel '0', ip 192.168.1.2:21000, user0, "
            "is complete created.")
        self.assertEqual(len(self.pilot_srvc.joined), 1)

    def test_user_left(self):

        def on_user_left(info):
            self.assertIsInstance(info, dict)
            self.assertEqual(info.get('channel'), 0)
            self.assertEqual(info.get('ip'), "192.168.1.2")
            self.assertEqual(info.get('callsign'), "user0")
            self.assertEqual(
                info.get('reason'), PILOT_LEAVE_REASON.DISCONNECTED)

        self.pilot_srvc.receiver = on_user_left
        self.parser.parse_line(
            "socketConnection with 192.168.1.2:21000 on channel 0 lost.  "
            "Reason: ")
        self.parser.parse_line("Chat: --- user0 has left the game.")
        self.assertEqual(len(self.pilot_srvc.left), 1)

        def on_user_kicked(info):
            self.assertIsInstance(info, dict)
            self.assertEqual(info.get('channel'), 1)
            self.assertEqual(info.get('ip'), "192.168.1.3")
            self.assertEqual(info.get('callsign'), "user1")
            self.assertEqual(
                info.get('reason'), PILOT_LEAVE_REASON.KICKED)

        self.pilot_srvc.receiver = on_user_kicked
        self.parser.parse_line(
            "socketConnection with 192.168.1.3:21000 on channel 1 lost.  "
            "Reason: You have been kicked from the server.")
        self.parser.parse_line("Chat: --- user1 has left the game.")
        self.assertEqual(len(self.pilot_srvc.left), 2)


class DeviceLinkParserTestCase(TestCase):

    def setUp(self):
        self.parser = DeviceLinkParser()

    def tearDown(self):
        self.parser = None

    def test_pilot_count(self):
        result = self.parser.pilot_count('0')
        self.assertEqual(result, 0)

    def test_pilot_pos(self):
        result = self.parser.pilot_pos('0:user0;100;200;300')
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('idx'), 0)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertIsInstance(result.get('pos'), dict)
        self.assertEqual(result['pos'].get('x'), 100)
        self.assertEqual(result['pos'].get('y'), 200)
        self.assertEqual(result['pos'].get('z'), 300)

    def test_all_pilots_pos(self):
        datas = ["{0}:user{0};{1};{2};{3}".format(
            i, i*100, i*200, i*300) for i in xrange(10)]
        results = self.parser.all_pilots_pos(datas)
        self.assertIsInstance(results, list)
        self.assertEqual(len(datas), len(results))
        for i in xrange(len(results)):
            result = results[i]
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get('idx'), i)
            self.assertEqual(result.get('callsign'), "user{0}".format(i))
            self.assertIsInstance(result.get('pos'), dict)
            self.assertEqual(result['pos'].get('x'), i*100)
            self.assertEqual(result['pos'].get('y'), i*200)
            self.assertEqual(result['pos'].get('z'), i*300)

    def test_static_count(self):
        result = self.parser.static_count('0')
        self.assertEqual(result, 0)

    def test_static_pos(self):
        result = self.parser.static_pos('0:0_Static;100;200;300')
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('idx'), 0)
        self.assertEqual(result.get('name'), "0_Static")
        self.assertIsInstance(result.get('pos'), dict)
        self.assertEqual(result['pos'].get('x'), 100)
        self.assertEqual(result['pos'].get('y'), 200)
        self.assertEqual(result['pos'].get('z'), 300)

    def test_all_static_pos(self):
        datas = ["{0}:{0}_Static;{1};{2};{3}".format(
            i, i*100, i*200, i*300) for i in xrange(10)]
        results = self.parser.all_static_pos(datas)
        self.assertIsInstance(results, list)
        self.assertEqual(len(datas), len(results))
        for i in xrange(len(results)):
            result = results[i]
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get('idx'), i)
            self.assertEqual(result.get('name'), "{0}_Static".format(i))
            self.assertIsInstance(result.get('pos'), dict)
            self.assertEqual(result['pos'].get('x'), i*100)
            self.assertEqual(result['pos'].get('y'), i*200)
            self.assertEqual(result['pos'].get('z'), i*300)
