# -*- coding: utf-8 -*-

from zope.interface import Interface


class ILineParser(Interface):

    def parse_line(self, line):
        """Parse line.

        :param line: line to parse.
        :type line: str.

        :returns: bool -- True if line was successfully parsed, otherwise False.
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
