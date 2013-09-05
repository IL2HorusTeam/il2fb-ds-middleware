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

    def seat_occupied(self, info):
        """
        """

    def weapons_loaded(self, info):
        """
        """

    def was_killed(self, info):
        """
        """

    def was_shot_down(self, info):
        """
        """

    def selected_army(self, info):
        """
        """

    def went_to_menu(self, info):
        """
        """


class IObjectsService(Interface):

    def was_destroyed(self, info):
        """
        """
