# -*- coding: utf-8 -*-

from twisted.internet.defer import Deferred

from il2ds_middleware.ds_emulator.tests.base import BaseTestCase


class DeviceLinkTestCase(BaseTestCase):

    def test_radar_refresh(self):
        d = Deferred()
        self.dl_client.receiver = self._get_unexpecting_line_receiver(d)
        self.dl_client.radar_refresh()
        return d

    # def test_pilot_count(self):
    #     responses = ["A/1002\\\\0", ]
    #     d = Deferred()
    #     self._set_dl_expecting_receiver(responses, d)
    #     self.dl_client.pilot_count()
    #     return d
