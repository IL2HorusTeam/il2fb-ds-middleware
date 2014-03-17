# -*- coding: utf-8 -*-
import re

from il2ds_log_parser.regex import RX_CALLSIGN

__all__ = [
    'RX_FLAGS', 'RX_USER_JOIN', 'RX_USER_LEFT', 'RX_USER_CHAT',
]

#------------------------------------------------------------------------------
# Commons
#------------------------------------------------------------------------------

"""Flags to be used for matching strings."""
RX_FLAGS = re.VERBOSE

RX_CHANNEL = """
# Capturing user's channel number. E.g.:
#
# "  0  "
#
# "0" will be captured into 'channel' group.
                # any beginning of the string
(?P<channel>    # 'channel' group start
    \d+         # one or more digits
)               # 'channel' group end
                # any ending of the string
"""

RX_IPv4 = """
# Capturing user's IPv4 address number. E.g.:
#
# "  192.168.1.2  "
#
# "192.168.1.2" will be captured into 'ip' group.
                # any beginning of the string
(?P<ip>         # 'ip' group start
    \d{1,3}     # 1 to 3 digits
    .           # point separator
    \d{1,3}     # 1 to 3 digits
    .           # point separator
    \d{1,3}     # 1 to 3 digits
    .           # point separator
    \d{1,3}     # 1 to 3 digits
)               # 'ip' group end
                # any ending of the string
"""

#-------------------------------------------------------------------------------
# Console events
#-------------------------------------------------------------------------------

RX_USER_JOIN = """
# Capturing `pilot joined server` event. E.g.:
#
# "socket channel '0', ip 192.168.1.2:21000, user0, is complete created"
#
# "user0" will be captured into 'callsign' group,
# "0" will be captured into 'channel' group,
# "192.168.1.2" will be captured into 'ip' group.
^               # beginning of the string
socket          #
\s              # single whitespace
channel         #
\s              # single whitespace
'               # opening quotemark
{channel}       # 'channel' group regex placeholder
'               # closing quotemark
,               # comma
\s              # single whitespace
ip              #
\s              # single whitespace
{ip}            # 'ip' group regex placeholder
:               # a colon
\d+             # one or more digits for remote port number
,               # comma
\s              # single whitespace
{callsign}      # 'callsign' group regex placeholder
,               # comma
\s              # single whitespace
is              #
\s              # single whitespace
complete        #
\s              # single whitespace
created         #
$               # end of the string
""".format(channel=RX_CHANNEL, ip=RX_IPv4, callsign=RX_CALLSIGN)

RX_USER_LEFT = """
# Capturing `pilot left server` event. E.g.:
#
# "socketConnection with 192.168.1.2:21000 on channel 0 lost.  Reason: You have been kicked from the server"
#
# "192.168.1.2" will be captured into 'ip' group,
# "0" will be captured into 'channel' group,
# "You have been kicked from the server" will be captured into 'reason' group.
^               # beginning of the string
socketConnection
\s              # single whitespace
with            #
\s              # single whitespace
{ip}            # 'ip' group regex placeholder
:               # a colon
\d+             # one or more digits for remote port number
\s              # single whitespace
on              #
\s              # single whitespace
channel         #
\s              # single whitespace
{channel}       # 'channel' group regex placeholder
\s              # single whitespace
lost.           #
\s+             # one ore more whitespaces
Reason:         #
\s              # single whitespace
(?P<reason>     # 'reason' group start
    .*          # any zero or more symbols
)               # 'reason' group end
$               # end of the string
""".format(ip=RX_IPv4, channel=RX_CHANNEL)

RX_USER_CHAT = """
# Capturing pilot's chat message. E.g.:
#
# "Chat: user0: \\ttest_message"
#
# "user0" will be captured into 'callsign' group,
# "test_message" will be captured into 'msg' group.
^               # beginning of the string
Chat:           #
\s              # single whitespace
{callsign}      # 'callsign' group regex placeholder
:               # colon
\s              # single whitespace
{sep}           # message separator placeholder
(?P<msg>        # 'msg' group start
    .*          # any zero or more symbols
)               # 'msg' group end
$               # end of the string
""".format(sep=r'\\t', callsign=RX_CALLSIGN)
