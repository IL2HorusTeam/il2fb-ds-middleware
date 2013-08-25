# -*- coding: utf-8 -*-

import datetime

from twisted.application.internet import TimerService
from twisted.internet import defer


class LogWatchingService(TimerService):

    receiver = None
    log_file = None

    def __init__(self, log_path, interval):
        self.log_path = log_path
        TimerService.__init__(self, interval, self.do_watch)

    def do_watch(self):
        self.log_file.seek(self.log_file.tell())
        if self.receiver is not None:
            for line in self.log_file.readlines():
                time, data = self._parse_line(line)
                if data is not None:
                    self.receiver(data)

    def _parse_line(self, line):
        idx = line.find(']')
        time_raw = line[1:idx]
        format = "%I:%M:%S %p"
        try:
            time = datetime.datetime.strptime(time_raw, format)
        except:
            format = "%b %d, %Y " + format
            try:
                time = datetime.datetime.strptime(time_raw, format)
            except:
                return (None, None)
        finally:
            data = line[idx + 1:].lstrip()
            return time, data

    def startService(self):
        if self.log_path is None:
            return
        self.log_file = open(self.log_path, 'r')
        TimerService.startService(self)

    def stopService(self):
        if self.log_file is None:
            return defer.succeed(None)
        else:
            self.log_file.close()
            self.log_file = None
            return TimerService.stopService(self)
