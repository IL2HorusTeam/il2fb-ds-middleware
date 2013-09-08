# -*- coding: utf-8 -*-

from twisted.trial.unittest import TestCase

from il2ds_middleware.constants import MISSION_STATUS, PILOT_LEAVE_REASON
from il2ds_middleware.parser import (ConsoleParser, EventLogParser,
    EventLogPassthroughParser, DeviceLinkParser, )
from il2ds_middleware.tests.service import (PilotService, ObjectsService,
    MissionService, )


class ConsoleParserTestCase(TestCase):

    def setUp(self):
        self.pilot_srvc = PilotService()
        self.mission_srvc = MissionService()
        self.parser = ConsoleParser((self.pilot_srvc, self.mission_srvc))
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
        status, mission = self.parser.mission_status(datas)
        self.assertEqual(status, MISSION_STATUS.LOADED)
        self.assertEqual(mission, "net/dogfight/test.mis")

    def test_mission_begin(self):
        status, mission = self.parser.mission_status([
            "Mission: net/dogfight/test.mis is Playing", ])
        self.assertEqual(status, MISSION_STATUS.PLAYING)
        self.assertEqual(mission, "net/dogfight/test.mis")

    def test_mission_end(self):
        self.parser.mission_status([
            "Mission: net/dogfight/test.mis is Playing", ])
        status, mission = self.parser.mission_status([
            "Mission: net/dogfight/test.mis is Loaded", ])
        self.assertEqual(status, MISSION_STATUS.LOADED)
        self.assertEqual(mission, "net/dogfight/test.mis")

    def test_mission_destroy(self):
        status, mission = self.parser.mission_status([
            "Mission NOT loaded", ])
        self.assertEqual(status, MISSION_STATUS.NOT_LOADED)
        self.assertEqual(mission, None)

    def test_user_joined(self):
        self.parser.parse_line(
            "socket channel '0' start creating: ip 192.168.1.2:21000")
        self.parser.parse_line("Chat: --- user0 joins the game.")
        self.parser.parse_line(
            "socket channel '0', ip 192.168.1.2:21000, user0, "
            "is complete created.")
        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        info = self.pilot_srvc.buffer[0]

        self.assertIsInstance(info, dict)
        self.assertEqual(info.get('channel'), 0)
        self.assertEqual(info.get('ip'), "192.168.1.2")
        self.assertEqual(info.get('callsign'), "user0")

    def test_user_left(self):
        self.parser.parse_line(
            "socketConnection with 192.168.1.2:21000 on channel 0 lost.  "
            "Reason: ")
        self.parser.parse_line("Chat: --- user0 has left the game.")
        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        info = self.pilot_srvc.buffer[0]

        self.assertIsInstance(info, dict)
        self.assertEqual(info.get('channel'), 0)
        self.assertEqual(info.get('ip'), "192.168.1.2")
        self.assertEqual(info.get('callsign'), "user0")
        self.assertEqual(info.get('reason'), PILOT_LEAVE_REASON.DISCONNECTED)

        self.parser.parse_line(
            "socketConnection with 192.168.1.3:21000 on channel 1 lost.  "
            "Reason: You have been kicked from the server.")
        self.parser.parse_line("Chat: --- user1 has left the game.")
        self.assertEqual(len(self.pilot_srvc.buffer), 2)
        info = self.pilot_srvc.buffer[1]

        self.assertIsInstance(info, dict)
        self.assertEqual(info.get('channel'), 1)
        self.assertEqual(info.get('ip'), "192.168.1.3")
        self.assertEqual(info.get('callsign'), "user1")
        self.assertEqual(info.get('reason'), PILOT_LEAVE_REASON.KICKED)

    def test_user_chat(self):
        self.parser.parse_line("Chat: user0: \\ttest_message")
        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        info = self.pilot_srvc.buffer[0]

        self.assertIsInstance(info, tuple)
        callsign, msg = info
        self.assertEqual(callsign, "user0")
        self.assertEqual(msg, "test_message")

    def test_parse_line_mission_status(self):
        self.parser.parse_line("mission test.mis is Playing")
        self.assertEqual(len(self.mission_srvc.buffer), 1)

        info = self.mission_srvc.buffer[0]
        self.assertIsInstance(info, tuple)
        status, mission = info
        self.assertEqual(status, MISSION_STATUS.PLAYING)
        self.assertEqual(mission, "test.mis")


class EventLogPassthroughParserTestCase(TestCase):

    def setUp(self):
        self.parser = EventLogPassthroughParser()

    def test_passthrough(self):
        methods = [
            self.parser.parse_line, self.parser.seat_occupied,
            self.parser.weapons_loaded, self.parser.was_killed,
            self.parser.was_shot_down, self.parser.selected_army,
            self.parser.went_to_menu, self.parser.was_destroyed,
            self.parser.in_flight, self.parser.landed,
            self.parser.damaged, self.parser.damaged_on_ground,
            self.parser.turned_wingtip_smokes, self.parser.crashed,
            self.parser.bailed_out, self.parser.was_captured,
            self.parser.was_captured, self.parser.was_wounded,
            self.parser.was_heavily_wounded, self.parser.removed, ]
        data = "test"
        for m in methods:
            self.assertEqual(m(data), data)


class EventLogParserTestCase(TestCase):

    def setUp(self):
        self.pilot_srvc = PilotService()
        self.obj_srvc = ObjectsService()
        self.parser = EventLogParser((self.pilot_srvc, self.obj_srvc))
        self.pilot_srvc.startService()

    def tearDown(self):
        self.pilot_srvc.stopService()
        self.obj_srvc.stopService()

    def _test_pos(self, pos):
        self.assertIsInstance(pos, dict)
        self.assertEqual(pos.get('x'), 100.99)
        self.assertEqual(pos.get('y'), 200.99)

    def test_occupied_seat(self):
        data = "user0:A6M2-21(0) seat occupied by user0 at 100.99 200.99"
        self.parser.parse_line(data)

        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        result = self.pilot_srvc.buffer[0]

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('seat'), 0)
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_weapons_loaded(self):
        data = "user0:A6M2-21 loaded weapons '1xdt' fuel 100%"
        self.parser.parse_line(data)

        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        result = self.pilot_srvc.buffer[0]

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self.assertEqual(result.get('weapons'), "1xdt")
        self.assertEqual(result.get('fuel'), 100)

    def test_was_killed(self):
        data = "user0:A6M2-21(0) was killed at 100.99 200.99"
        self.parser.parse_line(data)

        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        result = self.pilot_srvc.buffer[0]

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('seat'), 0)
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def _test_was_shot_down(self, attacker):
        data = "user0:A6M2-21 shot down by {:} at 100.99 200.99".format(
            attacker)
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result.get('victim'), dict)
        self.assertEqual(result['victim'].get('callsign'), "user0")
        self.assertEqual(result['victim'].get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

        self.assertIsInstance(result.get('attacker'), dict)
        return result['attacker']

    def test_was_shot_down_by_user(self):
        attacker = self._test_was_shot_down("user1:B5N2")
        self.assertEqual(attacker.get('is_user'), True)
        self.assertEqual(attacker.get('callsign'), "user1")
        self.assertEqual(attacker.get('aircraft'), "B5N2")

    def test_was_shot_down_by_ground(self):
        attacker = self._test_was_shot_down("landscape")
        self.assertEqual(attacker.get('is_user'), False)
        self.assertEqual(attacker.get('name'), "landscape")

    def test_was_shot_down_by_static(self):
        attacker = self._test_was_shot_down("0_Static")
        self.assertEqual(attacker.get('is_user'), False)
        self.assertEqual(attacker.get('name'), "0_Static")

    def test_was_shot_down_by_building(self):
        attacker = self._test_was_shot_down("0_bld")
        self.assertEqual(attacker.get('is_user'), False)
        self.assertEqual(attacker.get('name'), "0_bld")

    def test_selected_army(self):
        data = "user0 selected army Red at 100.99 200.99"
        self.parser.parse_line(data)

        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        result = self.pilot_srvc.buffer[0]

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('army'), 'Red')
        self._test_pos(result.get('pos'))

    def test_went_to_menu(self):
        data = "user0 entered refly menu"
        self.parser.parse_line(data)

        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        result = self.pilot_srvc.buffer[0]

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")

    def test_was_destroyed(self):
        data = "0_Static destroyed by landscape at 100.99 200.99"
        self.parser.parse_line(data)

        self.assertEqual(len(self.obj_srvc.buffer), 1)
        result = self.obj_srvc.buffer[0]

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('victim'), "0_Static")
        self.assertEqual(result.get('attacker'), "landscape")
        self._test_pos(result.get('pos'))

    def test_in_flight(self):
        data = "user0:A6M2-21 in flight at 100.99 200.99"
        self.parser.parse_line(data)

        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        result = self.pilot_srvc.buffer[0]

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_landed(self):
        data = "user0:A6M2-21 landed at 100.99 200.99"
        self.parser.parse_line(data)
        data = "A6M2-21 landed at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 2)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('is_user'), True)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

        result = self.pilot_srvc.buffer[1]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('is_user'), False)
        self.assertEqual(result.get('name'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def _test_was_damaged(self, attacker):
        data = "user0:A6M2-21 damaged by {:} at 100.99 200.99".format(
            attacker)
        self.parser.parse_line(data)

        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        result = self.pilot_srvc.buffer[0]

        self.assertIsInstance(result, dict)
        self.assertIsInstance(result.get('victim'), dict)
        self.assertEqual(result['victim'].get('callsign'), "user0")
        self.assertEqual(result['victim'].get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

        self.assertIsInstance(result.get('attacker'), dict)
        return result['attacker']

    def test_damaged_by_user(self):
        attacker = self._test_was_damaged("user1:B5N2")
        self.assertEqual(attacker.get('is_user'), True)
        self.assertEqual(attacker.get('callsign'), "user1")
        self.assertEqual(attacker.get('aircraft'), "B5N2")

    def test_damaged_by_landscape(self):
        attacker = self._test_was_damaged("landscape")
        self.assertEqual(attacker.get('is_user'), False)
        self.assertEqual(attacker.get('name'), "landscape")

    def test_damaged_by_static(self):
        attacker = self._test_was_damaged("0_Static")
        self.assertEqual(attacker.get('is_user'), False)
        self.assertEqual(attacker.get('name'), "0_Static")

    def test_damaged_by_building(self):
        attacker = self._test_was_damaged("0_bld")
        self.assertEqual(attacker.get('is_user'), False)
        self.assertEqual(attacker.get('name'), "0_bld")

    def test_damaged_on_ground(self):
        data = "user0:A6M2-21 damaged on the ground at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_turned_wingtip_smokes(self):
        data = "user0:A6M2-21 turned wingtip smokes on at 100.99 200.99"
        self.parser.parse_line(data)
        data = "user0:A6M2-21 turned wingtip smokes off at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 2)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self.assertEqual(result.get('state'), "on")
        self._test_pos(result.get('pos'))

        result = self.pilot_srvc.buffer[1]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self.assertEqual(result.get('state'), "off")
        self._test_pos(result.get('pos'))

    def test_crashed(self):
        data = "user0:A6M2-21 crashed at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_bailed_out(self):
        data = "user0:A6M2-21(0) bailed out at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('seat'), 0)
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_was_captured(self):
        data = "user0:A6M2-21(0) was captured at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('seat'), 0)
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_was_wounded(self):
        data = "user0:A6M2-21(0) was wounded at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('seat'), 0)
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_was_heavily_wounded(self):
        data = "user0:A6M2-21(0) was heavily wounded at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('seat'), 0)
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_removed(self):
        data = "user0:A6M2-21 removed at 100.99 200.99"
        self.parser.parse_line(data)
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        result = self.pilot_srvc.buffer[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertEqual(result.get('aircraft'), "A6M2-21")
        self._test_pos(result.get('pos'))

    def test_fake_data(self):
        result = self.parser.parse_line("some fake data")
        self.assertFalse(result)


class DeviceLinkParserTestCase(TestCase):

    def setUp(self):
        self.parser = DeviceLinkParser()

    def tearDown(self):
        self.parser = None

    def test_pilot_count(self):
        result = self.parser.pilot_count('0')
        self.assertEqual(result, 0)

    def test_pilot_pos(self):
        result = self.parser.pilot_pos('0:user0_0;100;200;300')
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('idx'), 0)
        self.assertEqual(result.get('callsign'), "user0")
        self.assertIsInstance(result.get('pos'), dict)
        self.assertEqual(result['pos'].get('x'), 100)
        self.assertEqual(result['pos'].get('y'), 200)
        self.assertEqual(result['pos'].get('z'), 300)

    def test_all_pilots_pos(self):
        datas = ["{0}:user{0}_{0};{1};{2};{3}".format(
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
