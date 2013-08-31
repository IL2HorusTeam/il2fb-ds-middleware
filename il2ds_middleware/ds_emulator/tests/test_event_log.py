# -*- coding: utf-8 -*-

import tempfile

from twisted.internet.defer import Deferred

from il2ds_middleware.ds_emulator.tests.base import BaseEmulatorTestCase


class EventLogTestCase(BaseEmulatorTestCase):

    def setUp(self):
        self.timeout_value = 0.5
        self.log_path = tempfile.mktemp()
        return super(EventLogTestCase, self).setUp()

    def test_event_log(self):
        pilots = self.service.getServiceNamed('pilots')
        missions = self.service.getServiceNamed('missions')
        static = self.service.getServiceNamed('static')

        responses = [
            "Mission: net/dogfight/test.mis is Playing\n",
            "Mission BEGIN\n",
            "user0 has connected\n",
            "user0:A6M2-21(0) seat occupied by user0 at 0 0\n",
            "user0:A6M2-21 loaded weapons '1xdt' fuel 100%\n",
            "user0:A6M2-21(0) was killed at 0 0\n",
            "0_Static destroyed by landscape at 0 0\n",
            "Mission END\n", ]
        d = Deferred()
        self._set_event_log_expecting_receiver(responses, d)

        missions.load("net/dogfight/test.mis")
        missions.begin()
        self.log_watcher.startService()

        static.spawn("0_Static")
        pilots.join("user0", "192.168.1.2")
        pilots.spawn("user0")
        pilots.kill("user0")
        static.destroy("0_Static")
        missions.end()
        return d
