# -*- coding: utf-8 -*-

from zope.interface import Interface


class ILineParser(Interface):

    def parse_line(self, line):
        """
        Parse line.

        :param line: line to parse.
        :type line: str.
        """


class IConsoleParser(ILineParser):

    def server_info(self, lines):
        """
        """

    def mission_status(self, lines):
        """
        """

    def user_joined(self, line):
        """
        """

    def user_left(self, line):
        """
        """

    def user_chat(self, line):
        """
        """


class IEventLogParser(ILineParser):

    def seat_occupied(self, data):
        """
        """

    def weapons_loaded(self, data):
        """
        """

    def was_killed(self, data):
        """
        """

    def was_shot_down(self, data):
        """
        """

    def selected_army(self, data):
        """
        """

    def went_to_menu(self, data):
        """
        """

    def was_destroyed(self, data):
        """
        """

    def in_flight(self, data):
        """
        """

    def landed(self, data):
        """
        """

    def damaged(self, data):
        """
        """

    def damaged_on_ground(self, data):
        """
        """

    def turned_wingtip_smokes(self, data):
        """
        """

    def crashed(self, data):
        """
        """

    def bailed_out(self, data):
        """
        """

    def was_captured(self, data):
        """
        """

    def was_wounded(self, data):
        """
        """

    def was_heavily_wounded(self, data):
        """
        """

    def removed(self, data):
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
