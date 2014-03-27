# -*- coding: utf-8 -*-
from zope.interface import Interface


__all__ = [
    'ILineParser', 'IConsoleParser', 'IDeviceLinkParser',
]


class ILineParser(Interface):
    """
    Interface for creating general-purpose string parsers.
    """

    def parse_line(line):
        """
        Parse line due to internal logic.

        Input:
        `line`      # A string line to parse.

        Output:
        Any object if line was successfully parsed, otherwise `None`.
        """


class IConsoleParser(ILineParser):
    """
    Parse server console's string messages.
    """

    def server_info(lines):
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

    def mission_status(lines):
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

    def user_joined(line):
        """
        Parse information about joined user.

        Input:
        `line`      # A string describing new server connection. Example:
                    # "socket channel '0', ip 192.168.1.2:21000, user0, is complete created."

        Output:
        An object providing information about connected user if the input line
        was successfully parsed. Otherwise `None`.
        """

    def user_left(line):
        """
        Parse information about disconnected user.

        Input:
        `line`      # A string describing disconnected user. Example:
                    # "socketConnection with 192.168.1.2:21000 on channel 0 lost.  Reason: "

        Output:
        An object providing information about disconnected user if the input
        line was successfully parsed. Otherwise `None`.
        """

    def user_chat(line):
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

    def users_common_info(lines):
        """
        Parse common information about users.

        Input:
        `lines`    # A sequence of strings which represents rows of a table
                   # with information about users. The table can be obtained by
                   # executing 'user' command in DS console. Example:
                   # [
                   #     " N      Name           Ping    Score   Army        Aircraft",
                   #     " 1      user1          3       0      (0)None              ",
                   #     " 2      user2          11      111    (1)Red       * Red 90    Il-2M_Late",
                   #     " 3      user3          22      222    (2)Blue      + 99        HurricaneMkIIb",
                   # ]

        Output:
        An object which provides common information about users.
        """

    def users_statistics(lines):
        """
        Parse detailed statistics about each user.

        Input:
        `lines`    # A sequence of strings which represents rows of multiple
                   # tables with information about users' statistics. The table
                   # can be obtained by executing 'user STAT' command in DS
                   # console. Example:
                   # [
                   #     "-------------------------------------------------------",
                   #     "Name: \t\t=user1",
                   #     "Score: \t\t0",
                   #     "State: \t\tIn Flight",
                   #     "Enemy Aircraft Kill: \t\t0",
                   #     "Enemy Static Aircraft Kill: \t\t0",
                   #     "Enemy Tank Kill: \t\t0",
                   #     "Enemy Car Kill: \t\t0",
                   #     "Enemy Artillery Kill: \t\t0",
                   #     "Enemy AAA Kill: \t\t0",
                   #     "Enemy Wagon Kill: \t\t0",
                   #     "Enemy Ship Kill: \t\t0",
                   #     "Enemy Radio Kill: \t\t0",
                   #     "Friend Aircraft Kill: \t\t0",
                   #     "Friend Static Aircraft Kill: \t\t0",
                   #     "Friend Tank Kill: \t\t0",
                   #     "Friend Car Kill: \t\t0",
                   #     "Friend Artillery Kill: \t\t0",
                   #     "Friend AAA Kill: \t\t0",
                   #     "Friend Wagon Kill: \t\t0",
                   #     "Friend Ship Kill: \t\t0",
                   #     "Friend Radio Kill: \t\t0",
                   #     "Fire Bullets: \t\t0",
                   #     "Hit Bullets: \t\t0",
                   #     "Hit Air Bullets: \t\t0",
                   #     "Fire Roskets: \t\t0",
                   #     "Hit Roskets: \t\t0",
                   #     "Fire Bombs: \t\t0",
                   #     "Hit Bombs: \t\t0",
                   #     "-------------------------------------------------------",
                   # ]

        Output:
        An object which provides information about users' statistics.
        """


class IDeviceLinkParser(Interface):
    """
    Parse string output from DeviceLink interface.
    """

    def pilot_count(data):
        """
        Parse information about currently active pilots.

        Input:
        `data`      # A string containing number of active pilots on server.
                    # Example:
                    # "0"

        Output:
        Any object containing information about currently active pilots.
        """

    def pilot_pos(data):
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

    def all_pilots_pos(datas):
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

    def static_count(data):
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

    def static_pos(data):
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

    def all_static_pos(datas):
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
