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
        request = {
            'command': OPCODE.RADAR_REFRESH.value,
        }
        self.dl_client.send_request(request)
        return d

    def test_pilot_count(self):
        responses = ["A/1002\\0", ]
        d = Deferred()
        self._set_dl_expecting_receiver(responses, d)
        request = {
            'command': OPCODE.PILOT_COUNT.value,
        }
        self.dl_client.send_request(request)
        return d
