# -*- coding: utf-8 -*-

from zope.interface import Interface

__all__ = [
    'ILineParser', 'IConsoleParser', 'IDeviceLinkParser',
]

class ILineParser(Interface):

    """Interface for creating general-purpose string parsers."""

    def parse_line(self, line):
        """
        Parse line due to internal logic.

        Input:
        `line`      # A string line to parse.

        Output:
        Any object if line was successfully parsed, otherwise `None`.
        """


class IConsoleParser(ILineParser):

    """Parse server console's string messages."""

    def server_info(self, lines):
        """
        Parse a sequence of lines containing information about server.

        Input:
        `lines`     # A sequence of strings providing information about server.
                    # Usually this information contains server's type, name and
                    # description. Each of them presented by a single line
                    # starting with a prefix. Prefix tells which kind of
                    # information a single line contains. Example:
                    # [
                    #     "Type: Local server",
                    #     "Name: server's name",
                    #     "Description: server's description"
                    # ]

        Output:
        A server describing object.
        """

    def mission_status(self, lines):
        """
        Parse information about mission's status.

        Input:
        `lines`     # A sequence of strings providing information about
                    # mission's status. They tell whether mission is loaded,
                    # is it playing or it is not loaded. Input strings are
                    # server's response for such commands as 'mission',
                    # 'mission LOAD', 'mission BEGIN'.

        Output:
        An object which describes current mission's status if the input line
        was successfully parsed. Otherwise `None`.
        """

    def user_joined(self, line):
        """
        Parse information about joined user.

        Input:
        `line`      # A string describing new server connection. Example:
                    # "socket channel '0', ip 192.168.1.2:21000, user0, is complete created."

        Output:
        An object providing information about connected user if the input line
        was successfully parsed. Otherwise `None`.
        """

    def user_left(self, line):
        """
        Parse information about disconnected user.

        Input:
        `line`      # A string describing disconnected user. Example:
                    # "socketConnection with 192.168.1.2:21000 on channel 0 lost.  Reason: "

        Output:
        An object providing information about disconnected user if the input
        line was successfully parsed. Otherwise `None`.
        """

    def user_chat(self, line):
        """
        Parse a message sent by user to the game chat.

        Input:
        `line`      # A string describing message sent by user to the game
                    # chat. Starts with 'Chat' prefix and contains sender's
                    # callsign and a body of the message. Example:
                    # "Chat: user0: \\tmessage"

        Output:
        An object providing information about message and its sender if the
        input line was successfully parsed. Otherwise `None`.
        """


class IDeviceLinkParser(Interface):

    """Parse string output from DeviceLink interface."""

    def pilot_count(self, data):
        """
        Parse information about currently active pilots.

        Input:
        `data`      # A string containing number of active pilots on server.
                    # Example:
                    # "0"

        Output:
        Any object containing information about currently active pilots.
        """

    def pilot_pos(self, data):
        """
        Parse string containing information about pilot's position coordinates.

        Input:
        `data`      # A string in '{id}:user{id}_{id};{x};{y};{z}' format,
                    # where x, y, z are integer values of pilot's coordinates.
                    # Example:
                    # "0:user0_0;100;200;300"

        Output:
        An object containing information about pilot's callsign and
        coordinates.
        """

    def all_pilots_pos(self, datas):
        """
        Pasrse a sequence of strings containing information about pilots'
        position coordinates.

        Input:
        `datas`     # A sequence of strings in
                    # '{id}:user{id}_{id};{x};{y};{z}', where x, y, z are
                    # integer values of pilot's coordinates. Example:
                    # [
                    #     "0:user0_0;100;200;300",
                    #     "1:user1_1;100;200;300",
                    # ]

        Output:
        A sequence of objects containing information about pilots' callsigns
        and coordinates.
        """

    def static_count(self, data):
        """
        Parse information about currently active static objects.

        Input:
        `data`      # A string containing number of active static objects on
                    # server. Example:
                    # "0"

        Output:
        Any object containing information about currently active static
        objects.
        """

    def static_pos(self, data):
        """
        Parse string containing information about static object's position
        coordinates.

        Input:
        `data`      # A string in '{id}:{id}_Static;{x};{y};{z}' format,
                    # where x, y, z are integer values of object's coordinates.
                    # Example:
                    # "0:0_Static;100;200;300"

        Output:
        An object containing information about static object's name and
        coordinates.
        """

    def all_static_pos(self, datas):
        """
        Pasrse a sequence of strings containing information about static
        objects' position coordinates.

        Input:
        `datas`     # A sequence of strings in '{id}:{id}_Static;{x};{y};{z}',
                    # where x, y, z are integer values of static objects'
                    # coordinates. Example:
                    # [
                    #     "0:0_Static;100;200;300",
                    #     "1:1_Static;100;200;300",
                    # ]

        Output:
        A sequence of objects containing information about static objects'
        names and coordinates.
        """
