# -*- coding: utf-8 -*-

import datetime

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
            "is complete created")
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

    def test_passthrough(self):
        parser = EventLogPassthroughParser()
        datas = [
            "test",
            "mission test.mis is Playing"
        ]
        for data in datas:
            self.assertEqual(parser.parse_line(data), data)


class EventLogParserTestCase(TestCase):

    def setUp(self):
        self.pilot_srvc = PilotService()
        self.obj_srvc = ObjectsService()
        self.mission_srvc = MissionService()
        self.parser = EventLogParser(
            (self.pilot_srvc, self.obj_srvc, self.mission_srvc))
        self.pilot_srvc.startService()

    def tearDown(self):
        self.pilot_srvc.stopService()
        self.obj_srvc.stopService()
        self.mission_srvc.stopService()

    def _last_event(self, data, evt_buffer, expected_size=1):
        self.parser.parse_line(data)
        self.assertEqual(len(evt_buffer), expected_size)
        evt = evt_buffer[-1]
        self.assertIsInstance(evt, dict)
        return evt

    def _last_pilots_event(self, data, expected_size=1):
        return self._last_event(data, self.pilot_srvc.buffer, expected_size)

    def _last_objects_event(self, data, expected_size=1):
        return self._last_event(data, self.obj_srvc.buffer, expected_size)

    def _last_mission_flow_event(self, data, expected_size=1):
        return self._last_event(data, self.mission_srvc.buffer, expected_size)

    def assertPos(self, data, x=100.99, y=200.99):
        pos = data.get('pos')
        self.assertIsNotNone(pos)
        self.assertIsInstance(pos, dict)
        self.assertEqual(pos.get('x'), x)
        self.assertEqual(pos.get('y'), y)

    def assertCalsignAircraft(self, data,
                              callsign="user0", aircraft="A6M2-21"):
        self.assertEqual(data.get('callsign'), callsign)
        self.assertEqual(data.get('aircraft'), aircraft)

    def assertAttackingUser(self, data,
                            callsign="user1", aircraft="B5N2"):
        attacker = data.get('attacker')
        self.assertIsNotNone(attacker)
        self.assertIsInstance(attacker, dict)
        self.assertCalsignAircraft(attacker, callsign, aircraft)

    def test_occupied_seat(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) seat occupied by user0 at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('seat'), 0)
        self.assertPos(evt)

    def test_selected_army(self):
        data = "[10:10:30 PM] user0 selected army Red at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('callsign'), "user0")
        self.assertEqual(evt.get('army'), "Red")
        self.assertPos(evt)

    def test_weapons_loaded(self):
        data = "[10:10:30 PM] user0:A6M2-21 loaded weapons '1xdt' fuel 100%"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('loadout'), "1xdt")
        self.assertEqual(evt.get('fuel'), 100)

    def test_went_to_menu(self):
        data = "[10:10:30 PM] user0 entered refly menu"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('callsign'), "user0")

    def test_was_killed(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was killed at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('seat'), 0)
        self.assertPos(evt)

    def test_was_killed_by_user(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was killed by user1:B5N2 at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('seat'), 0)
        self.assertAttackingUser(evt)
        self.assertPos(evt)

    def test_took_off(self):
        data = "[10:10:30 PM] user0:A6M2-21 in flight at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_landed(self):
        data = "[10:10:30 PM] user0:A6M2-21 landed at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_crashed(self):
        data = "[10:10:30 PM] user0:A6M2-21 crashed at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_toggle_wingtip_smokes(self):
        data = "[10:10:30 PM] user0:A6M2-21 turned wingtip smokes on at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('value'), True)
        self.assertPos(evt)

        data = "[10:10:30 PM] user0:A6M2-21 turned wingtip smokes off at 100.99 200.99"
        evt = self._last_pilots_event(data, expected_size=2)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('value'), False)
        self.assertPos(evt)

    def test_toggle_landing_lights(self):
        data = "[10:10:30 PM] user0:A6M2-21 turned landing lights on at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('value'), True)
        self.assertPos(evt)

        data = "[10:10:30 PM] user0:A6M2-21 turned landing lights off at 100.99 200.99"
        evt = self._last_pilots_event(data, expected_size=2)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('value'), False)
        self.assertPos(evt)

    def test_bailed_out(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) bailed out at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('seat'), 0)
        self.assertPos(evt)

    def test_parachute_opened(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) successfully bailed out at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('seat'), 0)
        self.assertPos(evt)

    def test_was_captured(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was captured at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('seat'), 0)
        self.assertPos(evt)

    def test_was_wounded(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was wounded at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('seat'), 0)
        self.assertPos(evt)

    def test_was_heavily_wounded(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was heavily wounded at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('seat'), 0)
        self.assertPos(evt)

    def test_destroyed_building(self):
        data = "[10:10:30 PM] 3do/Buildings/Industrial/FactoryHouse1_W/live.sim destroyed by user0:A6M2-21 at 100.99 200.99"
        evt = self._last_objects_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('building'), "FactoryHouse1_W")
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_destroyed_tree(self):
        data = "[10:10:30 PM] 3do/Tree/Line_W/live.sim destroyed by user0:A6M2-21 at 100.99 200.99"
        evt = self._last_objects_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('tree'), "Line_W")
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_destroyed_static(self):
        data = "[10:10:30 PM] 0_Static destroyed by user0:A6M2-21 at 100.99 200.99"
        evt = self._last_objects_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('static'), "0_Static")
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_destroyed_bridge(self):
        data = "[10:10:30 PM]  Bridge0 destroyed by user0:A6M2-21 at 100.99 200.99"
        evt = self._last_objects_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('bridge'), "Bridge0")
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_was_shot_down_by_user(self):
        data = "[10:10:30 PM] user0:A6M2-21 shot down by user1:B5N2 at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertAttackingUser(evt)
        self.assertPos(evt)

    def test_shot_down_self(self):
        data = "[10:10:30 PM] user0:A6M2-21 shot down by landscape at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_was_shot_down_by_static(self):
        data = "[10:10:30 PM] user0:A6M2-21 shot down by 0_Static at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt.get('static'), "0_Static")
        self.assertPos(evt)

    def test_damaged_self(self):
        data = "[10:10:30 PM] user0:A6M2-21 damaged by landscape at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_was_damaged_by_user(self):
        data = "[10:10:30 PM] user0:A6M2-21 damaged by user1:B5N2 at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertAttackingUser(evt)
        self.assertPos(evt)

    def test_was_damaged_on_the_ground(self):
        data = "[10:10:30 PM] user0:A6M2-21 damaged on the ground at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_mission_was_won(self):
        data = "[Dec 29, 2012 10:10:30 PM] Mission: RED WON"
        evt = self._last_mission_flow_event(data)
        self.assertEqual(evt.get('date'), datetime.date(2012, 12, 29))
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('army'), "Red")

    def test_target_complete(self):
        data = "[10:10:30 PM] Target 3 Complete"
        evt = self._last_mission_flow_event(data)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('number'), 3)
        self.assertEqual(evt.get('result'), True)

        data = "[10:10:30 PM] Target 5 Failed"
        evt = self._last_mission_flow_event(data, expected_size=2)
        self.assertEqual(evt.get('time'), datetime.time(22, 10, 30))
        self.assertEqual(evt.get('number'), 5)
        self.assertEqual(evt.get('result'), False)

    def test_fake_data(self):
        evt = self.parser.parse_line("some fake data")
        self.assertIsNone(evt)


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
        self.assertEqual(result.get('id'), 0)
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
            self.assertEqual(result.get('id'), i)
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
        self.assertEqual(result.get('id'), 0)
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
            self.assertEqual(result.get('id'), i)
            self.assertEqual(result.get('name'), "{0}_Static".format(i))
            self.assertIsInstance(result.get('pos'), dict)
            self.assertEqual(result['pos'].get('x'), i*100)
            self.assertEqual(result['pos'].get('y'), i*200)
            self.assertEqual(result['pos'].get('z'), i*300)
