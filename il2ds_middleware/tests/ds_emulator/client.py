# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from twisted.application import service

from il2ds_middleware.tests.ds_emulator.service import RootService


application = service.Application("server emulator")

root = RootService(("localhost", 20000))
root.setServiceParent(application)
