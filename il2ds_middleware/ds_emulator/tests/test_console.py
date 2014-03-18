# -*- coding: utf-8 -*-
from twisted.internet import defer

from il2ds_middleware.ds_emulator.tests.base import BaseEmulatorTestCase


def expected_join_responses(channel, callsign, ip, port):
    return [
        "socket channel '{0}' start creating: ip {1}:{2}\\n".format(
            channel, ip, port),
        "Chat: --- {0} joins the game.\\n".format(callsign),
        "socket channel '{0}', ip {1}:{2}, {3}, "
        "is complete created.\\n".format(
            channel, ip, port, callsign),
    ]


def expected_leave_responses(channel, callsign, ip, port):
    return [
        "socketConnection with {0}:{1} on channel {2} lost.  "
        "Reason: \\n".format(
            ip, port, channel),
        "Chat: --- {0} has left the game.\\n".format(
            callsign), ]


def expected_kick_responses(channel, callsign, ip, port):
    return [
        "socketConnection with {0}:{1} on channel {2} lost.  "
        "Reason: You have been kicked from the server.\\n".format(
            ip, port, channel),
        "Chat: --- {0} has left the game.\\n".format(
            callsign), ]


def expected_load_responses(path):
    return [
        "Loading mission {0}...\\n".format(path),
        "Load bridges\\n",
        "Load static objects\\n",
        "##### House without collision (3do/Tree/Tree2.sim)\\n",
        "##### House without collision (3do/Buildings/Port/Floor/live.sim)\\n",
        "##### House without collision (3do/Buildings/Port/BaseSegment/"
            "live.sim)\\n",
        "Mission: {0} is Loaded\\n".format(path), ]


class CommonsTestCase(BaseEmulatorTestCase):

    def test_connect(self):
        self.assertNotEqual(self.service.client, None)

    def test_disconnect(self):
        self.console_server_factory.on_connection_lost.addBoth(
            lambda unused: self.assertEqual(self.service.client, None))
        self.console_client_connector.disconnect()

    def test_receive_line(self):
        d = self.expect_console_lines([
            "test\\n",
        ])
        self.console_server.message("test")
        return d

    def test_unknown_command(self):
        d = self.expect_console_lines([
            "Command not found: abracadabracadabr\\n",
        ])
        self.console_client.sendLine("abracadabracadabr")
        return d

    @defer.inlineCallbacks
    def test_server_info(self):
        d = self.expect_console_lines([
            "Type: Local server\\n",
            "Name: Server\\n",
            "Description: \\n",
        ])
        self.console_client.sendLine("server")
        yield d

        self.service.set_server_info("Test server",
                                     "This is a server emulator")

        d = self.expect_console_lines([
            "Type: Local server\\n",
            "Name: Test server\\n",
            "Description: This is a server emulator\\n",
        ])
        self.console_client.sendLine("server")
        yield d


class PilotsTestCase(BaseEmulatorTestCase):

    def setUp(self):
        r = super(PilotsTestCase, self).setUp()
        self.srvc = self.service.getServiceNamed('pilots')
        return r

    def tearDown(self):
        self.srvc = None
        return super(PilotsTestCase, self).tearDown()

    def test_join(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.srvc.port))

        d = self.expect_console_lines(responses)
        self.srvc.join("user0", "192.168.1.2")
        self.srvc.join("user1", "192.168.1.3")
        return d

    @defer.inlineCallbacks
    def test_leave(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.srvc.port))
        responses.extend(expected_leave_responses(
            1, "user0", "192.168.1.2", self.srvc.port))

        d = self.expect_console_lines(responses)
        self.srvc.join("user0", "192.168.1.2")
        self.srvc.join("user1", "192.168.1.3")
        self.srvc.leave("user0")
        self.srvc.leave("fake_user")
        yield d
        self.assertEqual(len(self.srvc.pilots), 1)

    @defer.inlineCallbacks
    def test_kick_user(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.srvc.port))
        responses.extend(expected_kick_responses(
            3, "user1", "192.168.1.3", self.srvc.port))
        responses.extend(expected_kick_responses(
            1, "user0", "192.168.1.2", self.srvc.port))

        d = self.expect_console_lines(responses)
        self.srvc.join("user0", "192.168.1.2")
        self.srvc.join("user1", "192.168.1.3")
        self.console_client.sendLine("kick user1")
        self.console_client.sendLine("kick user0")
        yield d
        self.assertEqual(len(self.srvc.pilots), 0)

    @defer.inlineCallbacks
    def test_kick_number(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.srvc.port))
        responses.extend(expected_join_responses(
            5, "user2", "192.168.1.4", self.srvc.port))
        responses.extend(expected_kick_responses(
            5, "user2", "192.168.1.4", self.srvc.port))
        responses.extend(expected_kick_responses(
            1, "user0", "192.168.1.2", self.srvc.port))

        d = self.expect_console_lines(responses)
        self.srvc.join("user0", "192.168.1.2")
        self.srvc.join("user1", "192.168.1.3")
        self.srvc.join("user2", "192.168.1.4")
        self.console_client.sendLine("kick 3")
        self.console_client.sendLine("kick 1")
        yield d
        self.assertEqual(len(self.srvc.pilots), 1)

    def test_kick_number_invalid(self):
        self.assertEqual(len(self.srvc.pilots), 0)
        self.console_client.sendLine("kick 1")
        self.assertEqual(len(self.srvc.pilots), 0)

    @defer.inlineCallbacks
    def test_show_common_info(self):
        d = self.expect_console_lines([
            " N       Name           Ping    Score   Army        Aircraft\\n",
        ])
        self.console_client.sendLine("user")
        yield d

        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend([
            " N       Name           Ping    Score   Army        Aircraft\\n",
            " 1      user0            0       0      (0)None             \\n",
        ])
        d = self.expect_console_lines(responses)
        self.srvc.join("user0", "192.168.1.2")
        self.console_client.sendLine("user")
        yield d

        d = self.expect_console_lines([
            " N       Name           Ping    Score   Army        Aircraft\\n",
            " 1      user0            0       0      (0)None     * Red 1     A6M2-21\\n",
        ])
        self.srvc.spawn("user0")
        self.console_client.sendLine("user")
        yield d

    @defer.inlineCallbacks
    def test_show_statistics(self):
        d = self.expect_console_lines([
            "-------------------------------------------------------\\n",
        ])
        self.console_client.sendLine("user STAT")
        yield d

        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend([
            "-------------------------------------------------------\\n",
            "Name: \\t\\tuser0\\n",
            "Score: \\t\\t0\\n",
            "State: \\t\\tIDLE\\n",
            "Enemy Aircraft Kill: \\t\\t0\\n",
            "Enemy Static Aircraft Kill: \\t\\t0\\n",
            "Enemy Tank Kill: \\t\\t0\\n",
            "Enemy Car Kill: \\t\\t0\\n",
            "Enemy Artillery Kill: \\t\\t0\\n",
            "Enemy AAA Kill: \\t\\t0\\n",
            "Enemy Wagon Kill: \\t\\t0\\n",
            "Enemy Ship Kill: \\t\\t0\\n",
            "Enemy Radio Kill: \\t\\t0\\n",
            "Friend Aircraft Kill: \\t\\t0\\n",
            "Friend Static Aircraft Kill: \\t\\t0\\n",
            "Friend Tank Kill: \\t\\t0\\n",
            "Friend Car Kill: \\t\\t0\\n",
            "Friend Artillery Kill: \\t\\t0\\n",
            "Friend AAA Kill: \\t\\t0\\n",
            "Friend Wagon Kill: \\t\\t0\\n",
            "Friend Ship Kill: \\t\\t0\\n",
            "Friend Radio Kill: \\t\\t0\\n",
            "Fire Bullets: \\t\\t0\\n",
            "Hit Bullets: \\t\\t0\\n",
            "Hit Air Bullets: \\t\\t0\\n",
            "Fire Roskets: \\t\\t0\\n",
            "Hit Roskets: \\t\\t0\\n",
            "Fire Bombs: \\t\\t0\\n",
            "Hit Bombs: \\t\\t0\\n",
            "-------------------------------------------------------\\n",
        ])
        d = self.expect_console_lines(responses)
        self.srvc.join("user0", "192.168.1.2")
        self.console_client.sendLine("user STAT")
        yield d


class MissionsTestCase(BaseEmulatorTestCase):

    def setUp(self):
        result = super(MissionsTestCase, self).setUp()
        self.srvc = self.service.getServiceNamed('missions')
        return result

    def tearDown(self):
        self.srvc = None
        return super(MissionsTestCase, self).tearDown()

    def test_no_mission(self):
        d = self.expect_console_lines([
            "Mission NOT loaded\\n",
        ])
        self.console_client.sendLine("mission")
        return d

    def test_load_mission(self):
        responses = expected_load_responses("net/dogfight/test.mis")
        responses.append(responses[-1])

        d = self.expect_console_lines(responses)
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission")
        return d

    def test_begin_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append(responses[-1])

        d = self.expect_console_lines(responses)
        self.console_client.sendLine("mission BEGIN")
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission BEGIN")
        self.console_client.sendLine("mission")
        return d

    def test_end_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append("Mission: net/dogfight/test.mis is Loaded\\n")

        d = self.expect_console_lines(responses)
        self.console_client.sendLine("mission END")
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission BEGIN")
        self.console_client.sendLine("mission END")
        self.console_client.sendLine("mission END END END")
        self.console_client.sendLine("mission")
        return d

    def test_destroy_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append("Mission NOT loaded\\n")

        d = self.expect_console_lines(responses)
        self.console_client.sendLine("mission DESTROY")
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission DESTROY")
        self.console_client.sendLine("mission LOAD net/dogfight/test.mis")
        self.console_client.sendLine("mission BEGIN")
        self.console_client.sendLine("mission DESTROY")
        self.console_client.sendLine("mission")
        return d
