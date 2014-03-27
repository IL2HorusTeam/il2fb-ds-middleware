# -*- coding: utf-8 -*-
from twisted.trial.unittest import TestCase
from zope.interface.verify import verifyClass

from il2ds_middleware.constants import MISSION_STATUS
from il2ds_middleware.interface.service import (IPilotService, IObjectsService,
    IMissionService, )
from il2ds_middleware.service import (PilotBaseService, ObjectsBaseService,
    MissionBaseService, MissionService, )
from il2ds_middleware.tests.service import FakeLogWatchingService


verifyClass(IPilotService, PilotBaseService)
verifyClass(IObjectsService, ObjectsBaseService)
verifyClass(IMissionService, MissionBaseService)


class MissionServiceTestCase(TestCase):

    def setUp(self):
        self.log_watcher = FakeLogWatchingService()
        self.srvc = MissionService(self.log_watcher)
        self.srvc.startService()

    def tearDown(self):
        return self.srvc.stopService()

    def test_mission_begun(self):
        self.srvc.on_status_info((MISSION_STATUS.PLAYING, "test.mis"))
        self.assertTrue(self.log_watcher.running)
        self.assertEqual(self.srvc.mission, "test.mis")
        self.assertEqual(self.srvc.status, MISSION_STATUS.PLAYING)

    def test_mission_ended(self):
        self.srvc.mission = "test.mis"
        self.srvc.status = MISSION_STATUS.PLAYING
        self.log_watcher.startService()
        self.srvc.on_status_info((MISSION_STATUS.LOADED, "test.mis"))
        self.assertFalse(self.log_watcher.running)
        self.assertEqual(self.srvc.mission, "test.mis")
        self.assertEqual(self.srvc.status, MISSION_STATUS.LOADED)
