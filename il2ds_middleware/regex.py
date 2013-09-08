# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Map events
#-------------------------------------------------------------------------------

"""
' at 100.99 200.99'
"""
RX_POS = " at (\d+.\d+) (\d+.\d+)"
"""
'user0:aircraft0(0) seat occupied by user0 at 100.99 200.99'
"""
RX_SEAT_OCCUPIED = r"(.+):(.+)\((\d+)\) seat occupied by .+" + RX_POS
"""
'user0:aircraft0 loaded weapons 'default' fuel 100%'
"""
RX_WEAPONS_LOADED = r"(.+):(.+) loaded weapons \'(.+)\' fuel (\d+)%"
"""
'user0:aircraft0(0) was killed at 100.99 200.99'
"""
RX_KILLED = r"(.+):(.+)\((.+)\) was killed" + RX_POS
"""
'user0:aircraft0 shot down by user1:aircraft1 at 100.99 200.99'
'user0:aircraft0 shot down by 0_bld at 100.99 200.99'
'user0:aircraft0 shot down by 0_Static at 100.99 200.99'
'user0:aircraft0 shot down by landscape at 100.99 200.99'
"""
RX_SHOT_DOWN = r"(.+):(.+) shot down by (.+)" + RX_POS
"""
'user0 selected army Red at 100.99 200.99'
"""
RX_SELECTED_ARMY = r"(.+) selected army (.+)" + RX_POS
"""
'user0 entered refly menu'
"""
RX_WENT_TO_MENU = r"(.+) entered refly menu"
"""
'0_Static destroyed by 1_Static at 100.99 200.99'
"""
RX_DESTROYED = r"(.+) destroyed by (.+)" + RX_POS

#-------------------------------------------------------------------------------
# Console events
#-------------------------------------------------------------------------------

"""
'socket channel '0', ip 192.168.1.2:21000, user0, is complete created.'
"""
RX_USER_JOIN = r"socket channel '(\d+)', ip (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+, (.+), is complete created."
"""
'socketConnection with 192.168.1.2:21000 on channel 0 lost.  Reason: '
'socketConnection with 192.168.1.2:21000 on channel 0 lost.  Reason: You have been kicked from the server'
"""
RX_USER_LEFT = r"socketConnection with (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+ on channel (\d+) lost.  Reason: (.*)"
"""
'Chat: user0: \\ttest_message'
"""
RX_USER_CHAT = r"Chat: (.+): \\t(.*)"
