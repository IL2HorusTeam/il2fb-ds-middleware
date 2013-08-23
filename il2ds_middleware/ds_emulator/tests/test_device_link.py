# -*- coding: utf-8 -*-

from twisted.internet.defer import Deferred

from il2ds_middleware.protocol import DEVICE_LINK_OPCODE as OPCODE
from il2ds_middleware.ds_emulator.tests.base import BaseTestCase


class DeviceLinkTestCase(BaseTestCase):

    def test_wrong_format(self):
        d = Deferred()
        self.dl_client.receiver = self._get_unexpecting_line_receiver(d)
        self.dl_client.transport.write("HELLO/WORLD", self.dl_client.address)
        return d

    def test_unknown_command(self):
        d = Deferred()
        self.dl_client.receiver = self._get_unexpecting_line_receiver(d)
        request = {
            'command': 'fake_command',
        }
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
        1. user1 joins
        2. user2 joins
        3. check count => 0
        4. refresh radar
        5. check count => 0
        6. spawn user1
        7. check count => 0
        8. refresh radar
        9. check count => 1
        10. spawn user2
        11. check count => 1
        12. refresh radar
        13. check count => 2
        14. idle user1
        15. check count => 2
        16. refresh radar
        17. check count => 1
        """
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_pilots = OPCODE.PILOT_COUNT.make_command()

        pilots = self.service.getServiceNamed('pilots')

        def request_count_with_refresh():
            self.dl_client.send_request(cmd_pilots)
            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_request(cmd_pilots)

        def do_spawn1(_):
            responses2 = ["A/1002\\0", "A/1002\\1", ]
            d2 = Deferred()
            self._set_dl_expecting_receiver(responses2, d2)
            d2.addCallback(do_spawn2)

            pilots.spawn('user1')
            request_count_with_refresh()
            return d2

        def do_spawn2(_):
            responses3 = ["A/1002\\1", "A/1002\\2", ]
            d3 = Deferred()
            self._set_dl_expecting_receiver(responses3, d3)
            d3.addCallback(do_idle)

            pilots.spawn('user2')
            request_count_with_refresh()
            return d3

        def do_idle(_):
            responses4 = ["A/1002\\2", "A/1002\\1", ]
            d4 = Deferred()
            self._set_dl_expecting_receiver(responses4, d4)

            pilots.idle('user1')
            request_count_with_refresh()
            return d4

        responses = ["A/1002\\0", "A/1002\\0", ]
        d = Deferred()
        self._set_dl_expecting_receiver(responses, d)
        d.addCallback(do_spawn1)

        pilots.join('user1', '192.168.1.2')
        pilots.join('user2', '192.168.1.3')
        request_count_with_refresh()
        return d
