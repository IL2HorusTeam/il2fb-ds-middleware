# -*- coding: utf-8 -*-

from zope.interface import Interface


class ILineBroadcaster(Interface):

    def broadcast_line(self, line):
        raise NotImplementedError
