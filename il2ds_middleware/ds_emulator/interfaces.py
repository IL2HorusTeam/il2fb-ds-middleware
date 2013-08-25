# -*- coding: utf-8 -*-

from zope.interface import Interface

from twisted.application.service import IService


class ILineBroadcaster(Interface):
    """
    All clients of dedicated server's console must receive the same output.
    This interface describes method for sending same data to all clients.
    """
    def broadcast_line(self, line):
        """Broadcast line to all console clients.

        :param line: line to broadcast.
        :type line: str.
        """


class IPilotService(IService):

    def join(self, callsign, ip):
        """Emulate joining pilot to server.

        :param callsign: pilot's callsign.
        :type callsign: str.

        :param ip: remote pilot's ip address.
        :type ip: str.
        """

    def leave(self, callsign):
        """Emulate disconnecting pilot from server.

        :param callsign: pilot's callsign.
        :type callsign: str.
        """

    def kick(self, callsign):
        """Emulate pilot kicking from server.

        :param callsign: pilot's callsign.
        :type callsign: str.
        """

    def idle(self, callsign):
        """Emulate setting pilot's state to IDLE. Usually it means going to
        the refly menu.

        :param callsign: pilot's callsign.
        :type callsign: str.
        """

    def spawn(self, callsign, craft, pos):
        """Emulate spawning pilot at map.

        :param callsign: pilot's callsign.
        :type callsign: str.

        :param craft: description of craft: name, weapons, fuel.
        :type craft: dict.

        :param pos: position on map: z, y, z.
        :type pos: dict.
        """

    def kill(self, callsign):
        """Emulate killing pilot.

        :param callsign: pilot's callsign.
        :type callsign: str.
        """

    def get_active(self):
        """Get pilots which are not in IDLE state.

        :returns: str list -- list of callsigns.
        """


class IMissionService(IService):

    def load(self, mission):
        """Emulate loading mission to server.

        :param mission: path to mission's file relatively to server's root.
        :type mission: str.
        """

    def begin(self):
        """Emulate beginning of loaded mission."""

    def end(self):
        """Emulate ending of running mission."""

    def destroy(self):
        """Emulate destroying of running or loaded mission."""


class IStaticObjectService(IService):

    def spawn(self, name, pos):
        """Emulate spawning object at map.

        :param name: objects map name.
        :type name: str.

        :param pos: position on map: z, y, z.
        :type pos: dict.
        """

    def destroy(self, name, attacker_name):
        """Emulate destroying object by attaker.

        :param name: objects map name.
        :type name: str.

        :param attacker_name: name of attaker.
        :type attacker_name: str.
        """

    def get_active(self):
        """Get objects which are not destriyed.

        :returns: str list -- list of names.
        """


class IDeviceLinkService(IService):

    def forget_everything(self):
        """Forget any knows pilots, ojects, etc.
        """

    def got_requests(self, requests, address, peer):
        """Process incoming requests.

        :param requests: list of requests to process.
        :type requests: list.

        :param address: (host, port) of request initiator.
        :type address: tuple.

        :param peer: protocol instance used for sending answers.
        :type peer: DeviceLinkProtocol.
        """


class IEventLogger(IService):

    def enlog(self, line):
        """Write line to log.

        :param line: line to write to log.
        :type line: str.
        """

    def start_log(self):
        """Start logging: open file for writing or appending, etc.
        """

    def stop_log(self):
        """Stop logging: close logging file, etc.
        """
