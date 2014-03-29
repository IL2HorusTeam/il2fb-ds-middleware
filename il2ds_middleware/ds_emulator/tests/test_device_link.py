# -*- coding: utf-8 -*-
from twisted.internet import defer

from il2ds_middleware.constants import (DeviceLinkCommand,
    DEVICE_LINK_OPCODE as OPCODE, )
from il2ds_middleware.ds_emulator.tests import BaseTestCase


class DeviceLinkTestCase(BaseTestCase):

    def test_wrong_format(self):
        d = self.expect_dl_lines()
        self.dl_client.transport.write("HELLO/WORLD", self.dl_client.address)
        return d

    def test_unknown_command(self):
        d = self.expect_dl_lines()
        request = DeviceLinkCommand('fake_command', None)
        self.dl_client.send_request(request)
        return d

    def test_radar_refresh(self):
        d = self.expect_dl_lines()
        cmd = OPCODE.RADAR_REFRESH.make_command()
        self.dl_client.send_request(cmd)
        return d

    @defer.inlineCallbacks
    def test_pilot_count(self):
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_count = OPCODE.PILOT_COUNT.make_command()

        pilots = self.server_service.getServiceNamed('pilots')

        def request_count_with_refresh():
            self.dl_client.send_request(cmd_count)
            self.dl_client.send_request(cmd_radar)
            self.dl_client.send_request(cmd_count)

        d = self.expect_dl_lines(["A/1002\\0", "A/1002\\0", ])
        pilots.join('user0', '192.168.1.2')
        pilots.join('user1', '192.168.1.3')
        request_count_with_refresh()
        yield d

        d = self.expect_dl_lines(["A/1002\\0", "A/1002\\1", ])
        pilots.spawn('user0')
        request_count_with_refresh()
        yield d

        d = self.expect_dl_lines(["A/1002\\1", "A/1002\\2", ])
        pilots.spawn('user1')
        request_count_with_refresh()
        yield d

        d = self.expect_dl_lines(["A/1002\\2", "A/1002\\1", ])
        pilots.idle('user0')
        request_count_with_refresh()
        yield d

    @defer.inlineCallbacks
    def test_pilot_pos(self):
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_pos0 = OPCODE.PILOT_POS.make_command(0)
        cmd_pos1 = OPCODE.PILOT_POS.make_command(1)

        pilots = self.server_service.getServiceNamed('pilots')

        d = self.expect_dl_lines(["A/1004\\0:BADINDEX", ])
        self.dl_client.send_request(OPCODE.PILOT_POS.make_command())
        self.dl_client.send_request(cmd_pos0)
        yield d

        d = self.expect_dl_lines(["A/1004\\0:user0_0;100;200;5", ])
        pilots.join('user0', '192.168.1.2')
        pilots.spawn('user0', pos={'x': 100, 'y': 200, 'z': 5, })
        self.dl_client.send_request(cmd_radar)
        self.dl_client.send_request(cmd_pos0)
        yield d

        d = self.expect_dl_lines(["A/1004\\0:INVALID", ])
        pilots.kill('user0')
        self.dl_client.send_request(cmd_pos0)
        yield d

        d = self.expect_dl_lines(["A/1004\\0:INVALID", ])
        pilots.idle('user0')
        self.dl_client.send_request(cmd_pos0)
        yield d

        d = self.expect_dl_lines(["A/1004\\0:BADINDEX", ])
        self.dl_client.send_request(cmd_radar)
        self.dl_client.send_request(cmd_pos0)
        yield d

        d = self.expect_dl_lines([
            "A/1004\\0:user0_0;400;500;90/1004\\1:user1_1;700;800;50", ])
        pilots.join('user1', '192.168.1.3')
        pilots.spawn('user0', pos={'x': 400, 'y': 500, 'z': 90, })
        pilots.spawn('user1', pos={'x': 700, 'y': 800, 'z': 50, })
        self.dl_client.send_request(cmd_radar)
        self.dl_client.send_requests([cmd_pos0, cmd_pos1, ])
        yield d

    @defer.inlineCallbacks
    def test_static_count(self):
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_count = OPCODE.STATIC_COUNT.make_command()

        static = self.server_service.getServiceNamed('statics')

        d = self.expect_dl_lines(["A/1014\\0", ])
        self.dl_client.send_request(cmd_count)
        yield d

        d = self.expect_dl_lines(["A/1014\\0", ])
        static.spawn('0_Static')
        static.spawn('1_Static')
        self.dl_client.send_request(cmd_count)
        yield d

        d = self.expect_dl_lines(["A/1014\\2", ])
        self.dl_client.send_request(cmd_radar)
        self.dl_client.send_request(cmd_count)
        yield d

        d = self.expect_dl_lines(["A/1014\\2", ])
        static.destroy('0_Static')
        self.dl_client.send_request(cmd_count)
        yield d

        d = self.expect_dl_lines(["A/1014\\1", ])
        self.dl_client.send_request(cmd_radar)
        self.dl_client.send_request(cmd_count)
        yield d

    @defer.inlineCallbacks
    def test_static_pos(self):
        cmd_radar = OPCODE.RADAR_REFRESH.make_command()
        cmd_pos0 = OPCODE.STATIC_POS.make_command(0)
        cmd_pos1 = OPCODE.STATIC_POS.make_command(1)
        cmd_pos_both = [cmd_pos0, cmd_pos1, ]

        static = self.server_service.getServiceNamed('statics')

        d = self.expect_dl_lines(["A/1016\\0:BADINDEX/1016\\1:BADINDEX", ])
        self.dl_client.send_request(OPCODE.STATIC_POS.make_command())
        self.dl_client.send_requests(cmd_pos_both)
        yield d

        d = self.expect_dl_lines(["A/1016\\0:BADINDEX/1016\\1:BADINDEX", ])
        static.spawn('0_Static', pos={'x': 100, 'y': 200, 'z': 300, })
        static.spawn('1_Static', pos={'x': 400, 'y': 500, 'z': 600, })
        self.dl_client.send_requests(cmd_pos_both)
        yield d

        d = self.expect_dl_lines([
            "A/1016\\0:0_Static;100;200;300"
             "/1016\\1:1_Static;400;500;600", ])
        self.dl_client.send_request(cmd_radar)
        self.dl_client.send_requests(cmd_pos_both)
        yield d

        d = self.expect_dl_lines([
            "A/1016\\0:INVALID"
             "/1016\\1:1_Static;400;500;600", ])
        static.destroy('0_Static')
        self.dl_client.send_requests(cmd_pos_both)
        yield d

        d = self.expect_dl_lines([
            "A/1016\\0:1_Static;400;500;600"
             "/1016\\1:BADINDEX", ])
        self.dl_client.send_request(cmd_radar)
        self.dl_client.send_requests(cmd_pos_both)
        yield d
