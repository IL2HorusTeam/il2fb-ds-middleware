# coding: utf-8

from il2fb.ds.middleware.exceptions import DSMiddlewareException


class DeviceLinkError(DSMiddlewareException):
    pass


class DeviceLinkValueError(DeviceLinkError, ValueError):
    pass
