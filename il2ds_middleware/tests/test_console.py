# -*- coding: utf-8 -*-

from twisted.internet import reactor
from twisted.trial.unittest import TestCase

from il2ds_middleware.protocol import ConsoleClientFactory as ClientFactory

from il2ds_middleware.ds_emulator.service import RootService as DSService
from il2ds_middleware.ds_emulator.protocol import ConsoleFactory as DSFactory


# class TestClientFactory(TestCase):

#     def setUp(self):
#         self.dsfactory = DSFactory()
#         self.dsservice = DSService(self.dsfactory)
#         self.dsport = reactor.listenTCP(0, self.dsfactory)

#         self.addCleanup(self.dsport.stopListening)
#         self.addCleanup(self.dsservice.stopService)

#         self.dsservice.startService()

#     def test_connect_with_wrong_address(self):
#         pass
