# -*- coding: utf-8 -*-

import re

__all__ = [
    'RX_USER_JOIN', 'RX_USER_LEFT', 'RX_USER_CHAT',
]

#-------------------------------------------------------------------------------
# Console events
#-------------------------------------------------------------------------------

"""Flags to be used for matching strings."""
RX_FLAGS = re.VERBOSE

"""
'socket channel '0', ip 192.168.1.2:21000, user0, is complete created.'
"""
RX_USER_JOIN = r"socket channel '(\d+)', ip (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+, (.+), is complete created"
"""
'socketConnection with 192.168.1.2:21000 on channel 0 lost.  Reason: '
'socketConnection with 192.168.1.2:21000 on channel 0 lost.  Reason: You have been kicked from the server'
"""
RX_USER_LEFT = r"socketConnection with (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+ on channel (\d+) lost.  Reason: (.*)"
"""
'Chat: user0: \\ttest_message'
"""
RX_USER_CHAT = r"Chat: (.+): \\t(.*)"
