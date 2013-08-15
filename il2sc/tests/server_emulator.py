# -*- coding: utf-8 -*-

from twisted.internet.protocol import ServerFactory
from twisted.python import log

from il2sc.console import ConsoleProtocol


class ConsoleServerFactory(ServerFactory):
    protocol = ConsoleProtocol
