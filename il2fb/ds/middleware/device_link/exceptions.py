# coding: utf-8


class DeviceLinkError(Exception):
    pass


class DeviceLinkValueError(DeviceLinkError, ValueError):
    pass
