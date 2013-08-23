# -*- coding: utf-8 -*-

from twisted.python.constants import ValueConstant, Values


class DEVICE_LINK_OPCODE(Values):
    """
    Constants representing operation codes for DeviceLink interface.
    """
    RADAR_REFRESH = ValueConstant("1001")
    PILOT_COUNT = ValueConstant("1002")


DEVICE_LINK_PREFIXES = {
    'answer': 'A',
    'request': 'R',
}

DEVICE_LINK_CMD_SEPARATOR = '/'
DEVICE_LINK_ARGS_SEPARATOR = '\\'
