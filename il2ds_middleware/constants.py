# -*- coding: utf-8 -*-

from twisted.python.constants import (ValueConstant, Values, NamedConstant,
    Names, )


class DeviceLinkValueConstant(ValueConstant):

    def make_command(self, *args):
        cmd = {
            'command': self.value,
        }
        if args:
           cmd['args'] = list(args)
        return cmd


class DEVICE_LINK_OPCODE(Values):
    """
    Constants representing operation codes for DeviceLink interface.
    """
    RADAR_REFRESH = DeviceLinkValueConstant("1001")
    PILOT_COUNT = DeviceLinkValueConstant("1002")


DEVICE_LINK_PREFIXES = {
    'answer': 'A',
    'request': 'R',
}

DEVICE_LINK_CMD_SEPARATOR = '/'
DEVICE_LINK_ARGS_SEPARATOR = '\\'


class MISSION_STATUS(Names):
    """
    Constants representing various mission status codes.
    """
    NOT_LOADED = NamedConstant()
    LOADED = NamedConstant()
    PLAYING = NamedConstant()


class PILOT_STATE(Names):
    """
    Constants representing pilot states provided by dedicated server.
    """
    IDLE = NamedConstant()
    SPAWN = NamedConstant()
    TKOFF = NamedConstant()
    INFLIGHT = NamedConstant()
