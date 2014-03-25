# -*- coding: utf-8 -*-
from twisted.internet import defer


class UnexpectedLineError(Exception):

    def __init__(self, line):
        self.line = line

    def __str__(self):
        return "Unexpected line: {0}".format(self.line)


def add_watchdog(deferred, timeout=None, callback=None):

    def _callback(value):
        if not watchdog.called:
            watchdog.cancel()
        return value

    deferred.addBoth(_callback)

    def on_timeout():
        if deferred.called:
            return
        if callback is not None:
            callback()
        else:
            defer.timeout(deferred)

    from twisted.internet import reactor
    watchdog = reactor.callLater(timeout or 0.05, on_timeout)
