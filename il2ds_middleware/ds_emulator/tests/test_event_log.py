# -*- coding: utf-8 -*-

import tempfile

from twisted.internet.defer import Deferred

from il2ds_middleware.ds_emulator.tests.base import BaseTestCase


class EventLogTestCase(BaseTestCase):

    def setUp(self):
        self.log_path = tempfile.mktemp()
        return BaseTestCase.setUp(self)

    def test_event_log(self):
        pilots = self.service.getServiceNamed('pilots')
        missions = self.service.getServiceNamed('missions')
        static = self.service.getServiceNamed('static')

        missions._load_mission("net/dogfight/test.mis")
        missions._begin_mission()
        static.spawn("0_Static")
        pilots.join("user0", "192.168.1.2")
        pilots.spawn("user0")
        pilots.kill("user0")
        static.destroy("0_Static")
        missions._end_mission()
