# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from twisted.application import internet, service

from il2ds_middleware.tests.ds_emulator.service import RootService
from il2ds_middleware.tests.ds_emulator.protocol import DSConsoleFactory

factory = DSConsoleFactory()
server = internet.TCPServer(20000, factory)
root = RootService(factory)

application = service.Application("server emulator")
root.setServiceParent(application)
server.setServiceParent(application)
