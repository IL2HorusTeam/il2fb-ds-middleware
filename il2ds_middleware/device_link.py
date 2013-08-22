# -*- coding: utf-8 -*-

from twisted.python.constants import ValueConstant, Values


class OPCODE(Values):

    """
    Constants representing operation codes for DeviceLink interface.
    """

    RADAR_REFRESH = ValueConstant("1001")
    PILOT_COUNT = ValueConstant("1002")
