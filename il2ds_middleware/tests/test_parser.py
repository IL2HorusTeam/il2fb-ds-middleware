# -*- coding: utf-8 -*-
import datetime

from twisted.trial.unittest import TestCase
from zope.interface.verify import verifyClass

from il2ds_middleware.interface.parser import (ILineParser, IConsoleParser,
    IDeviceLinkParser, )
from il2ds_middleware.constants import MISSION_STATUS, PILOT_LEAVE_REASON
from il2ds_middleware.parser import (ConsoleParser, ConsolePassthroughParser,
    DeviceLinkParser, DeviceLinkPassthroughParser, EventLogParser,
    EventLogPassthroughParser, )

from il2ds_middleware.tests.service import (PilotsService, ObjectsService,
    MissionsService, )


verifyClass(ILineParser, ConsoleParser)
verifyClass(IConsoleParser, ConsoleParser)

verifyClass(ILineParser, ConsolePassthroughParser)
verifyClass(IConsoleParser, ConsolePassthroughParser)

verifyClass(IDeviceLinkParser, DeviceLinkParser)
verifyClass(IDeviceLinkParser, DeviceLinkPassthroughParser)

verifyClass(ILineParser, EventLogParser)
verifyClass(ILineParser, EventLogPassthroughParser)


class ConsoleParserTestCase(TestCase):

    def setUp(self):
        self.pilot_srvc = PilotsService()
        self.mission_srvc = MissionsService()
        self.parser = ConsoleParser((self.pilot_srvc, self.mission_srvc))
        self.pilot_srvc.startService()

    def tearDown(self):
        return self.pilot_srvc.stopService()

    def test_server_info(self):
        datas = [
            "Type: Local server",
            "Name: Test server",
            "Description: Horus test server",
        ]

        result = self.parser.server_info(datas)
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {
            'type': "Local server",
            'name': "Test server",
            'description': "Horus test server",
        })

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
        self.assertEqual(result[0], "some fake data")

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

    def test_parse_line_mission_status(self):
        self.parser.parse_line("mission test.mis is Playing")
        self.assertEqual(len(self.mission_srvc.buffer), 1)

        info = self.mission_srvc.buffer[0]
        self.assertIsInstance(info, tuple)
        status, mission = info
        self.assertEqual(status, MISSION_STATUS.PLAYING)
        self.assertEqual(mission, "test.mis")

    def test_user_joined(self):
        self.parser.parse_line(
            "socket channel '1' start creating: ip 192.168.1.2:21000")
        self.parser.parse_line("Chat: --- user0 joins the game.")
        self.parser.parse_line(
            "socket channel '1', ip 192.168.1.2:21000, user0, "
            "is complete created")
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        info = self.pilot_srvc.buffer[0]
        self.assertIsInstance(info, dict)
        self.assertEqual(info, {
            'channel': 1,
            'ip': "192.168.1.2",
            'callsign': "user0",
        })

    def test_user_left(self):
        self.parser.parse_line(
            "socketConnection with 192.168.1.2:21000 on channel 1 lost.  "
            "Reason: ")
        self.parser.parse_line("Chat: --- user0 has left the game.")
        self.assertEqual(len(self.pilot_srvc.buffer), 1)

        info = self.pilot_srvc.buffer[0]
        self.assertIsInstance(info, dict)
        self.assertEqual(info, {
            'channel': 1,
            'ip': "192.168.1.2",
            'callsign': "user0",
            'reason': PILOT_LEAVE_REASON.DISCONNECTED,
        })

        self.parser.parse_line(
            "socketConnection with 192.168.1.3:21000 on channel 3 lost.  "
            "Reason: You have been kicked from the server.")
        self.parser.parse_line("Chat: --- user1 has left the game.")
        self.assertEqual(len(self.pilot_srvc.buffer), 2)

        info = self.pilot_srvc.buffer[1]
        self.assertIsInstance(info, dict)
        self.assertEqual(info, {
            'channel': 3,
            'ip': "192.168.1.3",
            'callsign': "user1",
            'reason': PILOT_LEAVE_REASON.KICKED,
        })

    def test_user_chat(self):
        self.parser.parse_line("Chat: user0: \\ttest_message")
        self.assertEqual(len(self.pilot_srvc.buffer), 1)
        info = self.pilot_srvc.buffer[0]

        self.assertIsInstance(info, tuple)
        callsign, msg = info
        self.assertEqual(callsign, "user0")
        self.assertEqual(msg, "test_message")

    def test_users_common_info(self):
        datas = [
            " N       Name           Ping    Score   Army        Aircraft",
            " 1      user1            3       0      (0)None             ",
            " 2      user2            11      111    (1)Red      * Red 90    Il-2M_Late",
            " 3      user3            22      222    (2)Blue     + 99        HurricaneMkIIb", ]
        all_info = self.parser.users_common_info(datas)
        self.assertIsInstance(all_info, dict)
        self.assertEqual(len(all_info), 3)

        info = all_info.get('user1')
        self.assertEqual(info, {
            'ping': 3,
            'score': 0,
            'army_code': 0,
        })

        info = all_info.get('user2')
        self.assertEqual(info, {
            'ping': 11,
            'score': 111,
            'army_code': 1,
            'aircraft': {
                'designation': "* Red 90",
                'code': "Il-2M_Late",
            }
        })

        info = all_info.get('user3')
        self.assertEqual(info, {
            'ping': 22,
            'score': 222,
            'army_code': 2,
            'aircraft': {
                'designation': "+ 99",
                'code': "HurricaneMkIIb",
            }
        })

    def test_users_statistics(self):
        datas = [
            "-------------------------------------------------------",
            "Name: \\t\\tuser1",
            "Score: \\t\\t999",
            "State: \\t\\tIn Flight",
            "Enemy Aircraft Kill: \\t\\t1",
            "Enemy Static Aircraft Kill: \\t\\t2",
            "Enemy Tank Kill: \\t\\t3",
            "Enemy Car Kill: \\t\\t4",
            "Enemy Artillery Kill: \\t\\t5",
            "Enemy AAA Kill: \\t\\t6",
            "Enemy Wagon Kill: \\t\\t7",
            "Enemy Ship Kill: \\t\\t8",
            "Enemy Radio Kill: \\t\\t9",
            "Friend Aircraft Kill: \\t\\t10",
            "Friend Static Aircraft Kill: \\t\\t11",
            "Friend Tank Kill: \\t\\t12",
            "Friend Car Kill: \\t\\t13",
            "Friend Artillery Kill: \\t\\t14",
            "Friend AAA Kill: \\t\\t15",
            "Friend Wagon Kill: \\t\\t16",
            "Friend Ship Kill: \\t\\t17",
            "Friend Radio Kill: \\t\\t18",
            "Fire Bullets: \\t\\t100",
            "Hit Bullets: \\t\\t19",
            "Hit Air Bullets: \\t\\t20",
            "Fire Roskets: \\t\\t50",
            "Hit Roskets: \\t\\t21",
            "Fire Bombs: \\t\\t30",
            "Hit Bombs: \\t\\t22",
            "-------------------------------------------------------", ]
        all_statistics = self.parser.users_statistics(datas)
        self.assertIsInstance(all_statistics, dict)
        self.assertEqual(len(all_statistics), 1)

        info = all_statistics.get('user1')
        self.assertEqual(info, {
            'score': 999,
            'state': "In Flight",
            'kills': {
                'enemy': {
                    'aircraft': 1,
                    'static_aircraft': 2,
                    'tank': 3,
                    'car': 4,
                    'artillery': 5,
                    'aaa': 6,
                    'wagon': 7,
                    'ship': 8,
                    'radio': 9,
                },
                'friend': {
                    'aircraft': 10,
                    'static_aircraft': 11,
                    'tank': 12,
                    'car': 13,
                    'artillery': 14,
                    'aaa': 15,
                    'wagon': 16,
                    'ship': 17,
                    'radio': 18,
                },
            },
            'weapons': {
                'bullets': {
                    'fire': 100,
                    'hit': 19,
                    'hit_air': 20,
                },
                'rockets': {
                    'fire': 50,
                    'hit': 21,
                },
                'bombs': {
                    'fire': 30,
                    'hit': 22,
                },
            },
        })


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
        self.pilot_srvc = PilotsService()
        self.obj_srvc = ObjectsService()
        self.mission_srvc = MissionsService()
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
        self.assertEqual(data['pos'], {'x': x, 'y': y, })

    def assertCalsignAircraft(self, data,
                              callsign="user0",
                              aircraft="A6M2-21"):
        self.assertEqual(data['callsign'], callsign)
        self.assertEqual(data['aircraft'], aircraft)

    def assertAttackingUser(self, data,
                            callsign="user1",
                            aircraft="B5N2"):
        self.assertCalsignAircraft(data['attacker'], callsign, aircraft)

    def test_occupied_seat(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) seat occupied by user0 at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['seat'], 0)
        self.assertPos(evt)

    def test_selected_army(self):
        data = "[10:10:30 PM] user0 selected army Red at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['callsign'], "user0")
        self.assertEqual(evt['army'], "Red")
        self.assertPos(evt)

    def test_weapons_loaded(self):
        data = "[10:10:30 PM] user0:A6M2-21 loaded weapons '1xdt' fuel 100%"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['loadout'], "1xdt")
        self.assertEqual(evt['fuel'], 100)

    def test_went_to_menu(self):
        data = "[10:10:30 PM] user0 entered refly menu"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['callsign'], "user0")

    def test_was_killed(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was killed at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['seat'], 0)
        self.assertPos(evt)

    def test_was_killed_by_user(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was killed by user1:B5N2 at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['seat'], 0)
        self.assertAttackingUser(evt)
        self.assertPos(evt)

    def test_took_off(self):
        data = "[10:10:30 PM] user0:A6M2-21 in flight at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_landed(self):
        data = "[10:10:30 PM] user0:A6M2-21 landed at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_crashed(self):
        data = "[10:10:30 PM] user0:A6M2-21 crashed at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_toggle_wingtip_smokes(self):
        data = "[10:10:30 PM] user0:A6M2-21 turned wingtip smokes on at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['value'], True)
        self.assertPos(evt)

        data = "[10:10:30 PM] user0:A6M2-21 turned wingtip smokes off at 100.99 200.99"
        evt = self._last_pilots_event(data, expected_size=2)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['value'], False)
        self.assertPos(evt)

    def test_toggle_landing_lights(self):
        data = "[10:10:30 PM] user0:A6M2-21 turned landing lights on at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['value'], True)
        self.assertPos(evt)

        data = "[10:10:30 PM] user0:A6M2-21 turned landing lights off at 100.99 200.99"
        evt = self._last_pilots_event(data, expected_size=2)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['value'], False)
        self.assertPos(evt)

    def test_bailed_out(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) bailed out at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['seat'], 0)
        self.assertPos(evt)

    def test_parachute_opened(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) successfully bailed out at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['seat'], 0)
        self.assertPos(evt)

    def test_was_captured(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was captured at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['seat'], 0)
        self.assertPos(evt)

    def test_was_wounded(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was wounded at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['seat'], 0)
        self.assertPos(evt)

    def test_was_heavily_wounded(self):
        data = "[10:10:30 PM] user0:A6M2-21(0) was heavily wounded at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['seat'], 0)
        self.assertPos(evt)

    def test_destroyed_building(self):
        data = "[10:10:30 PM] 3do/Buildings/Industrial/FactoryHouse1_W/live.sim destroyed by user0:A6M2-21 at 100.99 200.99"
        evt = self._last_objects_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['building'], "FactoryHouse1_W")
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_destroyed_tree(self):
        data = "[10:10:30 PM] 3do/Tree/Line_W/live.sim destroyed by user0:A6M2-21 at 100.99 200.99"
        evt = self._last_objects_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['tree'], "Line_W")
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_destroyed_static(self):
        data = "[10:10:30 PM] 0_Static destroyed by user0:A6M2-21 at 100.99 200.99"
        evt = self._last_objects_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['static'], "0_Static")
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_destroyed_bridge(self):
        data = "[10:10:30 PM]  Bridge0 destroyed by user0:A6M2-21 at 100.99 200.99"
        evt = self._last_objects_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['bridge'], "Bridge0")
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_was_shot_down_by_user(self):
        data = "[10:10:30 PM] user0:A6M2-21 shot down by user1:B5N2 at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertAttackingUser(evt)
        self.assertPos(evt)

    def test_shot_down_self(self):
        data = "[10:10:30 PM] user0:A6M2-21 shot down by landscape at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_was_shot_down_by_static(self):
        data = "[10:10:30 PM] user0:A6M2-21 shot down by 0_Static at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertEqual(evt['static'], "0_Static")
        self.assertPos(evt)

    def test_damaged_self(self):
        data = "[10:10:30 PM] user0:A6M2-21 damaged by landscape at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_was_damaged_by_user(self):
        data = "[10:10:30 PM] user0:A6M2-21 damaged by user1:B5N2 at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertAttackingUser(evt)
        self.assertPos(evt)

    def test_was_damaged_on_the_ground(self):
        data = "[10:10:30 PM] user0:A6M2-21 damaged on the ground at 100.99 200.99"
        evt = self._last_pilots_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertCalsignAircraft(evt)
        self.assertPos(evt)

    def test_mission_was_won(self):
        data = "[Dec 29, 2012 10:10:30 PM] Mission: RED WON"
        evt = self._last_mission_flow_event(data)
        self.assertEqual(evt['date'], datetime.date(2012, 12, 29))
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['army'], "Red")

    def test_target_complete(self):
        data = "[10:10:30 PM] Target 3 Complete"
        evt = self._last_mission_flow_event(data)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['number'], 3)
        self.assertEqual(evt['result'], True)

        data = "[10:10:30 PM] Target 5 Failed"
        evt = self._last_mission_flow_event(data, expected_size=2)
        self.assertEqual(evt['time'], datetime.time(22, 10, 30))
        self.assertEqual(evt['number'], 5)
        self.assertEqual(evt['result'], False)

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
        self.assertEqual(result, {
            'id': 0,
            'callsign': "user0",
            'pos': {'x': 100, 'y': 200, 'z': 300, },
        })

    def test_all_pilots_pos(self):
        datas = ["{0}:user{0}_{0};{1};{2};{3}".format(
            i, i*100, i*200, i*300) for i in xrange(10)]

        results = self.parser.all_pilots_pos(datas)
        self.assertIsInstance(results, list)
        self.assertEqual(len(datas), len(results))
        for i in xrange(len(results)):
            self.assertEqual(results[i], {
                'id': i,
                'callsign': "user{0}".format(i),
                'pos': {'x': i*100, 'y': i*200, 'z': i*300, },
            })

    def test_static_count(self):
        result = self.parser.static_count('0')
        self.assertEqual(result, 0)

    def test_static_pos(self):
        result = self.parser.static_pos('0:0_Static;100;200;300')
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {
            'id': 0,
            'name': "0_Static",
            'pos': {'x': 100, 'y': 200, 'z': 300, },
        })

    def test_all_static_pos(self):
        datas = ["{0}:{0}_Static;{1};{2};{3}".format(
            i, i*100, i*200, i*300) for i in xrange(10)]

        results = self.parser.all_static_pos(datas)
        self.assertIsInstance(results, list)
        self.assertEqual(len(datas), len(results))
        for i in xrange(len(results)):
            self.assertEqual(results[i], {
                'id': i,
                'name': "{0}_Static".format(i),
                'pos': {'x': i*100, 'y': i*200, 'z': i*300, },
            })

    def test_invalid_pos(self):
        result = self.parser._parse_pos('0:INVALID')
        self.assertIsNone(result)

        result = self.parser._parse_pos('0:BADINDEX')
        self.assertIsNone(result)
