# -*- coding: utf-8 -*-

import datetime

from twisted.application.internet import TimerService
from twisted.internet import defer
from twisted.trial.unittest import TestCase

from il2ds_middleware.ds_emulator.service import RootService
from il2ds_middleware.ds_emulator.protocol import DeviceLinkServerProtocol
from il2ds_middleware.ds_emulator.tests.protocol import (ConsoleServerFactory,
    ConsoleClientFactory, ConsoleClientProtocol, DeviceLinkClientProtocol, )


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
            data = line[idx+1:].lstrip()
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


class BaseTestCase(TestCase):

    log_watcher_interval = 0.1
    timeout_value = 0.05
    log_path = None

    def setUp(self):
        self.log_watcher = LogWatchingService(
            self.log_path, self.log_watcher_interval)
        self._listen_server()
        return self._connect_client()

    def _listen_server(self):
        self.console_server_factory = ConsoleServerFactory()
        self.service = RootService(self.console_server_factory, self.log_path)
        self.dl_server = DeviceLinkServerProtocol()

        self.console_server_factory.receiver = self.service.parse_line
        self.dl_server.on_requests = self.service.getServiceNamed(
            'dl').got_requests

        from twisted.internet import reactor
        self.console_server_port = reactor.listenTCP(
            0, self.console_server_factory, interface="127.0.0.1")
        self.dl_server_port = reactor.listenUDP(
            0, self.dl_server, interface="127.0.0.1")
        self.service.startService()

    def _connect_client(self):
        self.console_client_factory = ConsoleClientFactory()
        self.console_message = self.console_client_factory.message

        ds_host = self.dl_server_port.getHost()
        self.dl_client = DeviceLinkClientProtocol((ds_host.host, ds_host.port))

        from twisted.internet import reactor
        self.console_client_port = reactor.connectTCP(
            "127.0.0.1", self.console_server_port.getHost().port,
            self.console_client_factory)
        self.dl_client_port = reactor.listenUDP(0, self.dl_client)
        return self.console_client_factory.on_connection_made

    def tearDown(self):
        self.console_server_factory.on_data = None
        self.dl_server.on_request = None
        self.console_client_factory.receiver = None
        self.dl_client.receiver = None

        console_server_stopped = defer.maybeDeferred(
            self.console_server_port.stopListening)
        dl_server_stopped = defer.maybeDeferred(
            self.dl_server_port.stopListening)
        dl_client_stopped = defer.maybeDeferred(
            self.dl_client_port.stopListening)
        self.console_client_port.disconnect()

        return defer.gatherResults([
            console_server_stopped, dl_server_stopped, dl_client_stopped,
            self.console_client_factory.on_connection_lost,
            self.console_server_factory.on_connection_lost,
            self.log_watcher.stopService(), self.service.stopService(), ])

    def _make_timeout(self, callback):
        from twisted.internet import reactor
        return reactor.callLater(self.timeout_value, callback, None)

    def _get_unexpecting_line_receiver(self, d):

        def got_line(line):
            timeout.cancel()
            from twisted.trial.unittest import FailTest
            d.errback(FailTest("Unexpected data:\n\t{0}.".format(line)))

        timeout = self._make_timeout(d.callback)
        return got_line

    def _get_expecting_line_receiver(self, expected_lines, d):

        def got_line(line):
            try:
                self.assertEqual(line, expected_lines.pop(0))
            except Exception as e:
                timeout.cancel()
                d.errback(e)
            else:
                if expected_lines:
                    return
                timeout.cancel()
                d.callback(None)

        def on_timeout(_):
            from twisted.trial.unittest import FailTest
            d.errback(FailTest(
                'Timed out, remaining lines:\n\t'+'\n\t'.join(expected_lines)))

        timeout = self._make_timeout(on_timeout)
        return got_line

    def _set_console_expecting_receiver(self, expected_lines, d):
        self.console_client_factory.receiver = \
            self._get_expecting_line_receiver(expected_lines, d)

    def _set_dl_expecting_receiver(self, expected_lines, d):
        self.dl_client.receiver = \
            self._get_expecting_line_receiver(expected_lines, d)

    def _set_event_log_expecting_receiver(self, expected_lines, d):
        self.log_watcher.receiver = \
            self._get_expecting_line_receiver(expected_lines, d)
