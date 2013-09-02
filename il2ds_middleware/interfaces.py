# -*- coding: utf-8 -*-

from zope.interface import Interface


class ILineParser(Interface):

    def parse_line(self, line):
        """Parse line.

        :param line: line to parse.
        :type line: str..
        """


class IConsoleParser(ILineParser):

    def server_info(self, lines):
        """
        """

    def mission_status(self, lines):
        """
        """

    def mission_load(self, lines):
        """
        """

    def mission_begin(self, lines):
        """
        """

    def mission_end(self, lines):
        """
        """

    def mission_destroy(self, lines):
        """
        """

    def user_joined(self, line):
        """
        """

    def on_user_joined(self, info):
        """
        """

    def user_left(self, line):
        """
        """

    def on_user_left(self, info):
        """
        """


class IDeviceLinkParser(Interface):

    def pilot_count(self, data):
        """
        """

    def pilot_pos(self, data):
        """
        """

    def all_pilots_pos(self, datas):
        """
        """

    def static_count(self, data):
        """
        """

    def static_pos(self, data):
        """
        """

    def all_static_pos(self, datas):
        """
        """


class IEventLineGetter(Interface):

    def got_event_line(self, line, timestamp):
        """Process line from event log.

        :param line: line which describes event.
        :type line: str.

        :param timestamp: timestamp provided by log watching service.
        :type timestamp: datetime.
        """
