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
            channel, ip, port, callsign)]


def expected_leave_responses(channel, callsign, ip, port):
    return [
        "socketConnection with {0}:{1} on channel {2} lost.  "
        "Reason: \\n".format(
            ip, port, channel),
        "Chat: --- {0} has left the game.\\n".format(
            callsign)]


def expected_kick_responses(channel, callsign, ip, port):
    return [
        "socketConnection with {0}:{1} on channel {2} lost.  "
        "Reason: You have been kicked from the server.\\n".format(
            ip, port, channel),
        "Chat: --- {0} has left the game.\\n".format(
            callsign)]


def expected_load_responses(path):
    return [
        "Loading mission {0}...\\n".format(path),
        "Load bridges\\n",
        "Load static objects\\n",
        "##### House without collision (3do/Tree/Tree2.sim)\\n",
        "##### House without collision (3do/Buildings/Port/Floor/live.sim)\\n",
        "##### House without collision (3do/Buildings/Port/BaseSegment/"
            "live.sim)\\n",
        "Mission: {0} is Loaded\\n".format(path)]


class CommonsTestCase(BaseEmulatorTestCase):

    def test_connect(self):
        self.assertEqual(len(self.console_server_factory.clients), 1)

    def test_disconnect(self):
        self.console_server_factory.on_connection_lost.addBoth(
            lambda _: self.assertEqual(
                len(self.console_server_factory.clients), 0))
        self.console_client_connector.disconnect()

    def test_receive_line(self):
        d = defer.Deferred()
        responses = ["test\\n", ]
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(responses, d)
        self.console_server_factory.broadcast_line("test")
        return d

    def test_unknown_command(self):
        d = defer.Deferred()
        responses = ["Command not found: abracadabracadabr\\n", ]
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(responses, d)
        self.console_message("abracadabracadabr")
        return d

    def test_server_info(self):

        def do_test():
            responses =[
                "Type: Local server\\n",
                "Name: Server\\n",
                "Description: \\n",]
            d = defer.Deferred()
            self.console_client_factory.receiver = \
                self._get_expecting_line_receiver(responses, d)
            d.addCallback(change_info)
            self.console_message("server")
            return d

        def change_info(_):
            self.service.set_server_info(
                "Test server", "This is a server emulator")
            responses =[
                "Type: Local server\\n",
                "Name: Test server\\n",
                "Description: This is a server emulator\\n",]
            d = defer.Deferred()
            self.console_client_factory.receiver = \
                self._get_expecting_line_receiver(responses, d)
            self.console_message("server")
            return d

        return do_test()


class PilotsTestCase(BaseEmulatorTestCase):

    def setUp(self):
        r = super(PilotsTestCase, self).setUp()
        self.srvc = self.service.getServiceNamed('pilots')
        return r

    def tearDown(self):
        self.srvc = None
        return super(PilotsTestCase, self).tearDown()

    def _get_pilots_count_checker(self, expected_count):
        def check(_):
            self.assertEqual(len(self.srvc.pilots), expected_count)
        return check

    def test_join(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.srvc.port))

        d = defer.Deferred()
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(responses, d)
        d.addCallback(self._get_pilots_count_checker(2))

        self.srvc.join("user0", "192.168.1.2")
        self.srvc.join("user1", "192.168.1.3")
        return d

    def test_leave(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.srvc.port))
        responses.extend(expected_leave_responses(
            1, "user0", "192.168.1.2", self.srvc.port))

        d = defer.Deferred()
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(responses, d)
        d.addCallback(self._get_pilots_count_checker(1))
        self.srvc.join("user0", "192.168.1.2")
        self.srvc.join("user1", "192.168.1.3")
        self.srvc.leave("user0")
        self.srvc.leave("fake_user")
        return d

    def test_kick(self):
        responses = expected_join_responses(
            1, "user0", "192.168.1.2", self.srvc.port)
        responses.extend(expected_join_responses(
            3, "user1", "192.168.1.3", self.srvc.port))
        responses.extend(expected_kick_responses(
            1, "user0", "192.168.1.2", self.srvc.port))

        d = defer.Deferred()
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(responses, d)
        d.addCallback(self._get_pilots_count_checker(1))
        self.srvc.join("user0", "192.168.1.2")
        self.srvc.join("user1", "192.168.1.3")
        self.console_message("kick user0")
        return d


class MissionsTestCase(BaseEmulatorTestCase):

    def setUp(self):
        r = super(MissionsTestCase, self).setUp()
        self.srvc = self.service.getServiceNamed('missions')
        return r

    def tearDown(self):
        self.srvc = None
        return super(MissionsTestCase, self).tearDown()

    def test_no_mission(self):
        d = defer.Deferred()
        responses = ["Mission NOT loaded\\n", ]
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(responses, d)
        self.console_message("mission")
        return d

    def test_load_mission(self):
        responses = expected_load_responses("net/dogfight/test.mis")
        responses.append(responses[-1])

        d = defer.Deferred()
        self._set_console_expecting_receiver(responses, d)
        self.console_message("mission LOAD net/dogfight/test.mis")
        self.console_message("mission")
        return d

    def test_begin_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append(responses[-1])

        d = defer.Deferred()
        self._set_console_expecting_receiver(responses, d)
        self.console_message("mission BEGIN")
        self.console_message("mission LOAD net/dogfight/test.mis")
        self.console_message("mission BEGIN")
        self.console_message("mission")
        return d

    def test_end_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append("Mission: net/dogfight/test.mis is Loaded\\n")

        d = defer.Deferred()
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(responses, d)
        self.console_message("mission END")
        self.console_message("mission LOAD net/dogfight/test.mis")
        self.console_message("mission BEGIN")
        self.console_message("mission END")
        self.console_message("mission END END END")
        self.console_message("mission")
        return d

    def test_destroy_mission(self):
        responses = ["ERROR mission: Mission NOT loaded\\n", ]
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.extend(expected_load_responses("net/dogfight/test.mis"))
        responses.append("Mission: net/dogfight/test.mis is Playing\\n")
        responses.append("Mission NOT loaded\\n")

        d = defer.Deferred()
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(responses, d)
        self.console_message("mission DESTROY")
        self.console_message("mission LOAD net/dogfight/test.mis")
        self.console_message("mission DESTROY")
        self.console_message("mission LOAD net/dogfight/test.mis")
        self.console_message("mission BEGIN")
        self.console_message("mission DESTROY")
        self.console_message("mission")
        return d
