# -*- coding: utf-8 -*-

from twisted.python.constants import (ValueConstant, Values, NamedConstant,
    Names, )


class DeviceLinkValueConstant(ValueConstant):

    def make_command(self, arg=None):
        return (self.value, arg, )


class DEVICE_LINK_OPCODE(Values):
    """
    Constants representing operation codes for DeviceLink interface.
    """
    RADAR_REFRESH = DeviceLinkValueConstant("1001")
    PILOT_COUNT = DeviceLinkValueConstant("1002")
    PILOT_POS = DeviceLinkValueConstant("1004")
    STATIC_COUNT = DeviceLinkValueConstant("1014")
    STATIC_POS = DeviceLinkValueConstant("1016")


DEVICE_LINK_PREFIXES = {
    'answer': 'A',
    'request': 'R',
}

DEVICE_LINK_CMD_SEPARATOR = '/'
DEVICE_LINK_ARGS_SEPARATOR = '\\'
DEVICE_LINK_CMD_GROUP_MAX_SIZE = 40


class MISSION_STATUS(Names):
    """
    Constants representing various mission status codes.
    """
    NOT_LOADED = NamedConstant()
    LOADED = NamedConstant()
    PLAYING = NamedConstant()


class PILOT_STATE(Names):
    """
    Constants representing pilot states.
    """
    IDLE = NamedConstant()
    SPAWNED = NamedConstant()
    IN_FLIGHT = NamedConstant()
    DEAD = NamedConstant()


class OBJECT_STATE(Names):
    """
    Constants representing object states.
    """
    ALIVE = NamedConstant()
    DESTROYED = NamedConstant()


REQUEST_TIMEOUT = 0.1
REQUEST_MISSION_LOAD_TIMEOUT = 30


class PILOT_LEAVE_REASON(Names):
    """
    Constants representing the reason why a pilot has left.
    """
    DISCONNECTED = NamedConstant()
    KICKED = NamedConstant()
