# -*- coding: utf-8 -*-
import datetime
import os
import tempfile
import tx_logging

from twisted.internet import defer
from zope.interface import implementer
from zope.interface.verify import verifyClass

from il2ds_middleware.interface.parser import ILineParser
from il2ds_middleware.service import LogWatchingService

from il2ds_middleware.ds_emulator.tests import BaseTestCase
from il2ds_middleware.tests import expect_lines


LOG = tx_logging.getLogger(__name__)


@implementer(ILineParser)
class LogWatchingService(LogWatchingService):

    def got_line(self, line):
        try:
            time, line = self.parse_line(line)
        except ValueError:
            LOG.error("Failed to parse line:\n\t{0}".format(line))
        else:
            self.process_line(line)

    def process_line(self, line):
        pass

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


verifyClass(ILineParser, LogWatchingService)


class EventsLogTestCase(BaseTestCase):

    def setUp(self):
        self.fd, self.log_path = tempfile.mkstemp(prefix='ds_emulator_',
                                                  text=True)
        self.log_watcher = LogWatchingService(self.log_path, period=0.1)
        return super(EventsLogTestCase, self).setUp()

    @defer.inlineCallbacks
    def tearDown(self):
        if self.log_watcher.running:
            yield self.log_watcher.stopService()
        yield super(EventsLogTestCase, self).tearDown()
        os.close(self.fd)
        os.remove(self.log_path)

    def test_event_log(self):
        pilots = self.server_service.getServiceNamed('pilots')
        missions = self.server_service.getServiceNamed('missions')
        static = self.server_service.getServiceNamed('statics')

        self.log_watcher.process_line, d = expect_lines([
            "Mission: net/dogfight/test.mis is Playing\n",
            "Mission BEGIN\n",
            "user0 has connected\n",
            "user0:A6M2-21(0) seat occupied by user0 at 0 0\n",
            "user0:A6M2-21 loaded weapons '1xdt' fuel 100%\n",
            "user0:A6M2-21(0) was killed at 0 0\n",
            "0_Static destroyed by landscape at 0 0\n",
            "Mission END\n",
        ], timeout=0.5)

        missions.load("net/dogfight/test.mis")
        missions.begin()
        self.log_watcher.startService()

        static.spawn("0_Static")
        pilots.join("user0", "192.168.1.2")
        pilots.spawn("user0")
        pilots.kill("user0")
        static.destroy("0_Static")
        missions.end()

        return d
