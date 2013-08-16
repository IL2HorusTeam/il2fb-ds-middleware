# -*- coding: utf-8 -*-

from twisted.internet.protocol import ServerFactory
from twisted.python import log

from il2ds_proxy.console import ConsoleProtocol


class ConsoleServerFactory(ServerFactory):
    protocol = ConsoleProtocol
