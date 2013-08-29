# -*- coding: utf-8 -*-

from twisted.internet import defer
from twisted.trial.unittest import TestCase

from il2ds_middleware.tests.base import BaseTestCase
from il2ds_middleware.ds_emulator.service import RootService
from il2ds_middleware.ds_emulator.protocol import (DeviceLinkServerProtocol,
    ConsoleServerFactory, )
from il2ds_middleware.ds_emulator.tests.protocol import (ConsoleClientFactory,
    ConsoleClientProtocol, DeviceLinkClientProtocol, )
from il2ds_middleware.ds_emulator.tests.service import LogWatchingService


class BaseEmulatorTestCase(BaseTestCase):

    ConsoleClient = ConsoleClientFactory
    DeviceLinkClient = DeviceLinkClientProtocol
    LogWatcher = LogWatchingService
