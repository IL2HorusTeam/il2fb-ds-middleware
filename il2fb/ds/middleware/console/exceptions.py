# coding: utf-8

from il2fb.ds.middleware.exceptions import DSMiddlewareException


class ConsoleError(DSMiddlewareException):
    pass


class ConsoleRequestError(ConsoleError):
    pass
