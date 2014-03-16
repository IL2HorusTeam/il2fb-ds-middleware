# -*- coding: utf-8 -*-
from il2ds_middleware.tests.base import BaseTestCase
from il2ds_middleware.ds_emulator.tests.protocol import (ConsoleClientFactory,
    DeviceLinkClient, )
from il2ds_middleware.ds_emulator.tests.service import LogWatchingService


class BaseEmulatorTestCase(BaseTestCase):

    console_client_factory_class = ConsoleClientFactory
    dl_client_class = DeviceLinkClient
    log_watcher_class = LogWatchingService
