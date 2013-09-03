# -*- coding: utf-8 -*-

from zope.interface import Interface


class IEventLineGetter(Interface):

    def got_event_line(self, line, timestamp):
        """Process line from event log.

        :param line: line which describes event.
        :type line: str.

        :param timestamp: timestamp provided by log watching service.
        :type timestamp: datetime.
        """


class IPilotService(Interface):

    def user_join(self, info):
        """
        """

    def user_left(self, info):
        """
        """
