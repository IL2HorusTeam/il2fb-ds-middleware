# -*- coding: utf-8 -*-

import datetime

from twisted.python import log

from zope.interface import implementer

from il2ds_middleware.interface.parser import ILineParser
from il2ds_middleware.service import LogWatchingBaseService


@implementer(ILineParser)
class LogWatchingService(LogWatchingBaseService):

    receiver = None

    def got_line(self, line):
        try:
            time, data = self.parse_line(line)
        except ValueError:
            log.err("Failed to parse line:\n\t{0}".format(line))
        else:
            if self.receiver is not None:
                self.receiver(data)

    def parse_line(self, line):
        idx = line.find(']')
        time_raw = line[1:idx]
        format = "%I:%M:%S %p"
        try:
            time = datetime.datetime.strptime(time_raw, format)
        except ValueError:
            format = "%b %d, %Y " + format
            time = datetime.datetime.strptime(time_raw, format)
        finally:
            data = line[idx + 1:].lstrip()
            return time, data
