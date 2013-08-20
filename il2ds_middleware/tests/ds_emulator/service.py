# -*- coding: utf-8 -*-

from twisted.application import internet
from twisted.application.service import IService, Service, MultiService
from twisted.python import log
from zope.interface import implementer, Interface

from il2ds_middleware.tests.ds_emulator.interfaces import ILineBroadcaster
from il2ds_middleware.tests.ds_emulator.protocol import DSConsoleFactory


class ILineParser(Interface):

    def parse_line(self, line):
        """
        Return True if line was successfully parsed, otherwise return False.
        """
        raise NotImplementedError


class _PropagatorMixin:

    propagate = False

    def _autopropagate(self, value):
        return False if self.propagate else value


@implementer(IService, ILineBroadcaster)
class _LineBroadcastingServiceMixin:

    broadcaster = None

    def broadcast_line(self, line):
        if self.broadcaster:
            self.broadcaster.broadcast_line(line)
        elif self.parent:
            self.parent.broadcast_line(line)
        else:
            log.msg("Broadcasting into nowhere: \"{0}\"".format(line))


@implementer(ILineParser)
class _DSServiceMixin(_LineBroadcastingServiceMixin, _PropagatorMixin):
    pass


class RootService(MultiService, _DSServiceMixin):
    """
    Top-level service.
    """

    def __init__(self, broadcaster):
        MultiService.__init__(self)
        self.broadcaster = broadcaster
        self._init_children()

    def _init_children(self):
        """
        Initialize children services.
        """
        ChatService().setServiceParent(self)
        PilotService().setServiceParent(self)
        MissionService().setServiceParent(self)

    def startService(self):
        self.broadcaster.service = self
        MultiService.startService(self)

    def stopService(self):
        self.broadcaster.service = None
        return MultiService.stopService(self)

    def parse_line(self, line):
        result = False
        for service in self.services:
            if not ILineParser.providedBy(service):
                continue
            result = service.parse_line(line)
            if result:
                break
        return self._autopropagate(result)


class PilotService(Service, _DSServiceMixin):

    name = "pilots"

    def parse_line(self, line):
        # TODO:
        print self.name, line
        result = False
        return self._autopropagate(result)


class MissionService(Service, _DSServiceMixin):

    name = "missions"

    def parse_line(self, line):
        # TODO:
        print self.name, line
        result = False
        return self._autopropagate(result)


class ChatService(Service, _DSServiceMixin):

    name = "chat"
    propagate = True

    def parse_line(self, line):
        # TODO:
        print self.name, line
        result = False
        return self._autopropagate(result)
