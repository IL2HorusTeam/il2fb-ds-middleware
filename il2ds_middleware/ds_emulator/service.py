# -*- coding: utf-8 -*-

from twisted.application import internet
from twisted.application.service import IService, Service, MultiService
from twisted.python import log
from zope.interface import implementer, Interface

from il2ds_middleware.ds_emulator.interfaces import ILineBroadcaster


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
    channel = 1
    channel_inc = 2
    port = 21000

    def __init__(self):
        self.pilots = []

    def join(self, callsign, ip):

        def create_pilot():
            pilot = {
                'callsign': callsign,
                'ip': ip,
                'channel': self.channel,
            }
            self.channel += self.channel_inc
            return pilot

        pilot = create_pilot()
        self.pilots.append(pilot)

        self.broadcast_line(
            "socket channel '{0}' start creating: ip {1}:{2}".format(
                pilot['channel'], pilot['ip'], self.port))
        self.broadcast_line(
            "Chat: --- {0} joins the game.".format(
                pilot['callsign']))
        self.broadcast_line(
            "socket channel '{0}', ip {1}:{2}, {3}, " \
            "is complete created.".format(
                pilot['channel'], pilot['ip'], self.port, pilot['callsign']))

    def leave(self, callsign):
        pilot = self._pilot_by_callsign(callsign)
        if pilot is None:
            return

        self.pilots.remove(pilot)

        self.broadcast_line(
            "socketConnection with {0}:{1} on channel {2} lost.  " \
            "Reason: ".format(
                pilot['ip'], self.port, pilot['channel']))
        self.broadcast_line(
            "Chat: --- {0} has left the game.".format(
                pilot['callsign']))

    def _pilot_by_callsign(self, callsign):
        for p in self.pilots:
            if p['callsign'] == callsign:
                return p
        log.err("Pilot with callsign \"{0}\" not found.".format(callsign))
        return None

    def parse_line(self, line):
        # TODO:
        result = False
        return self._autopropagate(result)


MISSION_NONE, MISSION_LOADED, MISSION_PLAYING = 1, 2, 3


class MissionService(Service, _DSServiceMixin):

    name = "missions"
    status = MISSION_NONE
    mission = None

    def parse_line(self, line):
        result = line == "mission"
        if result:
            self._send_status()
        return self._autopropagate(result)

    def _send_status(self):
        if self.status == MISSION_NONE:
            self.broadcast_line("Mission NOT loaded")
            return


class ChatService(Service, _DSServiceMixin):

    name = "chat"
    propagate = True

    def parse_line(self, line):
        # TODO:
        result = False
        return self._autopropagate(result)
