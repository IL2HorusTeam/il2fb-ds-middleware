# -*- coding: utf-8 -*-
from twisted.internet import defer
from twisted.python.failure import Failure
from twisted.trial import unittest


class UnexpectedLineError(Exception):

    def __init__(self, line):
        self.line = line

    def __str__(self):
        return "Unexpected line: {0}".format(self.line)


def add_watchdog(deferred, timeout=None, callback=None):

    def clean_up(value):
        if not watchdog.called:
            watchdog.cancel()
        return value

    deferred.addBoth(clean_up)

    def on_timeout():
        if deferred.called:
            return
        if callback is not None:
            callback()
        else:
            defer.timeout(deferred)

    from twisted.internet import reactor
    watchdog = reactor.callLater(timeout or 0.05, on_timeout)


def expecting_line_receiver(expected_lines, timeout=None):
    expected_lines = expected_lines[:]

    def got_line(line):
        if d.called:
            return
        if expected_lines:
            try:
                assert line == expected_lines.pop(0)
            except Exception as e:
                d.errback(e)
            else:
                if not expected_lines:
                    d.callback(None)
        else:
            d.errback(Failure(UnexpectedLineError(line)))

    def on_timeout():
        d.errback(unittest.FailTest(
            "Timed out, remaining lines:\n{0}".format(
            "\n\t".join(["\"%s\"" % line for line in expected_lines]))))

    d = defer.Deferred()
    add_watchdog(d, timeout, on_timeout)
    return got_line, d


def unexpecting_line_receiver(timeout=None):

    def got_line(line):
        d.errback(Failure(UnexpectedLineError(line)))

    def errback(failure):
        failure.trap(defer.TimeoutError)

    d = defer.Deferred().addErrback(errback)
    add_watchdog(d, timeout)
    return got_line, d


def expect_lines(expected_lines=None, timeout=None):
    return expecting_line_receiver(expected_lines, timeout) \
           if expected_lines else unexpecting_line_receiver(timeout)
