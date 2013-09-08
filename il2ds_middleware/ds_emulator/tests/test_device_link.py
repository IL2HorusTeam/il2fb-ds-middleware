# -*- coding: utf-8 -*-

from twisted.internet.defer import Deferred

from il2ds_middleware.constants import DEVICE_LINK_OPCODE as OPCODE
from il2ds_middleware.ds_emulator.tests.base import BaseEmulatorTestCase


class DeviceLinkTestCase(BaseEmulatorTestCase):

    def test_wrong_format(self):
        d = Deferred()
        self.dl_client.receiver = self._get_unexpecting_line_receiver(d)
        self.dl_client.transport.write("HELLO/WORLD", self.dl_client.address)
        return d

    def test_unknown_command(self):
        d = Deferred()
        self.dl_client.receiver = self._get_unexpecting_line_receiver(d)
        request = ('fake_command', None, )
        self.dl_client.send_request(request)
        return d

    def test_radar_refresh(self):
        d = Deferred()
        self.dl_client.receiver = self._get_unexpecting_line_receiver(d)
        cmd = OPCODE.RADAR_REFRESH.make_command()
        self.dl_client.send_request(cmd)
        return d

    def test_pilot_count(self):
        """
        Scenario:
        1. user0 joins
        2. user1 joins
        3. check count => 0
        4. refresh radar
        5. check count => 0
        6. spawn user0
        7. check count => 0
        8. refresh radar
        9. check count => 1
        10. spawn user1
        11. check count => 1
        12. refresh radar
        13. check count => 2
        14. idle user0
        15. check count => 2
        16. refresh radar
        17. check count => 1
        """
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_count = OPCODE.PILOT_COUNT.make_command()

        pilots = self.service.getServiceNamed('pilots')

        def request_count_with_refresh():
            self.dl_client.send_request(cmd_count)
            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_request(cmd_count)

        def do_test():
            responses = ["A/1002\\0", "A/1002\\0", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_spawn0)

            pilots.join('user0', '192.168.1.2')
            pilots.join('user1', '192.168.1.3')
            request_count_with_refresh()
            return d

        def do_spawn0(_):
            responses = ["A/1002\\0", "A/1002\\1", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_spawn1)

            pilots.spawn('user0')
            request_count_with_refresh()
            return d

        def do_spawn1(_):
            responses = ["A/1002\\1", "A/1002\\2", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_idle)

            pilots.spawn('user1')
            request_count_with_refresh()
            return d

        def do_idle(_):
            responses = ["A/1002\\2", "A/1002\\1", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)

            pilots.idle('user0')
            request_count_with_refresh()
            return d

        return do_test()

    def test_pilot_pos(self):
        """
        Scenario:
        1. check pos with no index
        2. check user0 pos => 0:BADINDEX
        3. user0 joins
        4. user0 spawns at (100, 200, 5)
        5. check user0 pos => 0:user0_0;100;200;5
        6. kill user0
        7. check user0 pos => 0:INVALID
        8. idle user0
        9. check user0 pos => 0:INVALID
        10. refresh radar
        11. check user0 pos => 0:BADINDEX
        12. user1 joins
        13. user0 spawns at (400, 500, 90)
        14. user1 spawns at (700, 800, 50)
        15. refresh radar
        16. check user0 and user1 pos =>
                0:user0_0;400;500;90, 1:user1_1;700;800;50
        """
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_count = OPCODE.PILOT_COUNT.make_command()
        cmd_pos0 = OPCODE.PILOT_POS.make_command(0)
        cmd_pos1 = OPCODE.PILOT_POS.make_command(1)

        pilots = self.service.getServiceNamed('pilots')

        def do_test():
            responses = ["A/1004\\0:BADINDEX", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_join_and_spawn0)

            self.dl_client.send_request(OPCODE.PILOT_POS.make_command())
            self.dl_client.send_request(cmd_pos0)
            return d

        def do_join_and_spawn0(_):
            responses = ["A/1004\\0:user0_0;100;200;5", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_kill0)

            pilots.join('user0', '192.168.1.2')
            pilots.spawn('user0', pos={
                'x': 100, 'y': 200, 'z': 5, })
            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_request(cmd_pos0)
            return d

        def do_kill0(_):
            responses = ["A/1004\\0:INVALID", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_idle0)

            pilots.kill('user0')
            self.dl_client.send_request(cmd_pos0)
            return d

        def do_idle0(_):
            responses = ["A/1004\\0:INVALID", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_idle0_refreshed)

            pilots.idle('user0')
            self.dl_client.send_request(cmd_pos0)
            return d

        def do_idle0_refreshed(_):
            responses = ["A/1004\\0:BADINDEX", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_join1_and_spawn_both)

            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_request(cmd_pos0)
            return d

        def do_join1_and_spawn_both(_):
            responses = [
                "A/1004\\0:user0_0;400;500;90/1004\\1:user1_1;700;800;50", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)

            pilots.join('user1', '192.168.1.3')
            pilots.spawn('user0', pos={
                'x': 400, 'y': 500, 'z': 90, })
            pilots.spawn('user1', pos={
                'x': 700, 'y': 800, 'z': 50, })
            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_requests([cmd_pos0, cmd_pos1, ])
            return d

        return do_test()

    def test_static_count(self):
        """
        Scenario:
        1. check count => 0
        2. spawn 0_Static
        3. spawn 1_Static
        4. check count => 0
        5. refresh radar
        6. check count => 2
        7. destroy 0_Static
        8. check count => 2
        9. refresh radar
        10. check count => 1
        """
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_count = OPCODE.STATIC_COUNT.make_command()

        static = self.service.getServiceNamed('static')

        def do_test():
            responses = ["A/1014\\0", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_spawn)

            self.dl_client.send_request(cmd_count)
            return d

        def do_spawn(_):
            responses = ["A/1014\\0", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_refresh)

            static.spawn('0_Static')
            static.spawn('1_Static')
            self.dl_client.send_request(cmd_count)
            return d

        def do_refresh(_):
            responses = ["A/1014\\2", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_destroy0)

            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_request(cmd_count)
            return d

        def do_destroy0(_):
            responses = ["A/1014\\2", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_refresh_again)

            static.destroy('0_Static')
            self.dl_client.send_request(cmd_count)
            return d

        def do_refresh_again(_):
            responses = ["A/1014\\1", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)

            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_request(cmd_count)
            return d

        return do_test()

    def test_static_pos(self):
        """
        Scenario:
        1. check pos with no index
        2. check both pos => 0:BADINDEX, 1:BADINDEX
        3. 0_Static spawns at (100, 200, 300)
        4. 1_Static spawns at (400, 500, 600)
        5. check both pos => 0:BADINDEX, 1:BADINDEX
        6. refresh radar
        7. check both pos => 0:0_Static;100;200;300, 1:1_Static;400;500;600
        8. destroy 0_Static
        9. check both pos => 0:INVALID, 1:1_Static;400;500;600
        10. refresh radar
        11. check both pos => 0:1_Static;400;500;600, 0:BADINDEX
        """
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_pos0 = OPCODE.STATIC_POS.make_command(0)
        cmd_pos1 = OPCODE.STATIC_POS.make_command(1)
        cmd_pos_both = [cmd_pos0, cmd_pos1, ]

        static = self.service.getServiceNamed('static')

        def do_test():
            responses = ["A/1016\\0:BADINDEX/1016\\1:BADINDEX", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_spawn)

            self.dl_client.send_request(OPCODE.STATIC_POS.make_command())
            self.dl_client.send_requests(cmd_pos_both)
            return d

        def do_spawn(_):
            responses = ["A/1016\\0:BADINDEX/1016\\1:BADINDEX", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_refresh)

            static.spawn('0_Static', pos={
                'x': 100, 'y': 200, 'z': 300, })
            static.spawn('1_Static', pos={
                'x': 400, 'y': 500, 'z': 600, })
            self.dl_client.send_requests(cmd_pos_both)
            return d

        def do_refresh(_):
            responses = [
                "A/1016\\0:0_Static;100;200;300" \
                "/1016\\1:1_Static;400;500;600", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_destroy0)

            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_requests(cmd_pos_both)
            return d

        def do_destroy0(_):
            responses = [
                "A/1016\\0:INVALID" \
                "/1016\\1:1_Static;400;500;600", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)
            d.addCallback(do_refresh_again)

            static.destroy('0_Static')
            self.dl_client.send_requests(cmd_pos_both)
            return d

        def do_refresh_again(_):
            responses = ["A/1016\\0:1_Static;400;500;600/1016\\1:BADINDEX", ]
            d = Deferred()
            self._set_dl_expecting_receiver(responses, d)

            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_requests(cmd_pos_both)
            return d

        return do_test()
