# -*- coding: utf-8 -*-
import datetime
import tx_logging

from zope.interface import implementer

from il2ds_middleware.interface.parser import ILineParser
from il2ds_middleware.service import LogWatchingBaseService


LOG = tx_logging.getLogger(__name__)


@implementer(ILineParser)
class LogWatchingService(LogWatchingBaseService):

    receiver = None

    def got_line(self, line):
        try:
            time, data = self.parse_line(line)
        except ValueError:
            LOG.error("Failed to parse line:\n\t{0}".format(line))
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
