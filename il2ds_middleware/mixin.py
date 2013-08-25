# -*- coding: utf-8 -*-

from zope.interface import implementer

from twisted.python import log

from il2ds_middleware.interfaces import ILineParser


@implementer(ILineParser)
class PropagatingLineParserMixing:

    propagate = False

    def _autopropagate(self, value=True):
        return False if self.propagate else value
