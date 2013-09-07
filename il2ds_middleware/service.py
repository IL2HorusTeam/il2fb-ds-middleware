# -*- coding: utf-8 -*-

from twisted.application.internet import TimerService
from twisted.application.service import Service
from twisted.internet import defer
from twisted.python import log

from zope.interface import implementer

from il2ds_middleware.constants import MISSION_STATUS
from il2ds_middleware.interface.service import (IPilotService, IObjectsService,
    IMissionService, )
from il2ds_middleware.parser import EventLogPassthroughParser


class ClientBaseService(Service):

    """Console client is set up manually"""
    client = None


@implementer(IPilotService)
class PilotBaseService(ClientBaseService):

    def user_join(self, info):
        raise NotImplementedError

    def user_left(self, info):
        raise NotImplementedError

    def seat_occupied(self, info):
        raise NotImplementedError

    def weapons_loaded(self, info):
        raise NotImplementedError

    def was_killed(self, info):
        raise NotImplementedError

    def was_shot_down(self, info):
        raise NotImplementedError

    def selected_army(self, info):
        raise NotImplementedError

    def went_to_menu(self, info):
        raise NotImplementedError

    def user_chat(self, info):
        raise NotImplementedError


@implementer(IObjectsService)
class ObjectsBaseService(ClientBaseService):

    def was_destroyed(self, info):
        raise NotImplementedError


@implementer(IMissionService)
class MissionBaseService(ClientBaseService):

    def __init__(self, log_watcher):
        self.status = None
        self.mission = None
        self.log_watcher = log_watcher

    def on_status_info(self, (status, mission)):
        if status != self.status:
            if self.status == MISSION_STATUS.PLAYING:
                self.ended()
            elif status == MISSION_STATUS.PLAYING:
                self.began()
        self.status, self.mission = status, mission

    def began(self, info=None):
        self.log_watcher.startService()

    def ended(self, info=None):
        self.log_watcher.stopService()

    def stopService(self):

        def callback(_):
            ClientBaseService.stopService(self)

        return self.log_watcher.stopService().addBoth(callback)


class LogWatchingBaseService(TimerService):

    def __init__(self, log_path, interval=1):
        self.log_file = None
        self.log_path = log_path
        TimerService.__init__(self, interval, self.do_watch)

    def do_watch(self):
        self.log_file.seek(self.log_file.tell())
        for line in self.log_file.readlines():
            self.got_line(line)

    def got_line(self, line):
        raise NotImplementedError

    def startService(self):
        if self.log_file is not None:
            return
        try:
            self.log_file = open(self.log_path, 'r')
        except IOError as e:
            log.err("Failed to open events log: {:}.".format(e))
        else:
            self.log_file.seek(self.log_file.tell())
            self.log_file.readlines()
            TimerService.startService(self)

    def stopService(self):
        if self.log_file is None:
            return defer.succeed(None)
        else:
            self.log_file.close()
            self.log_file = None
            return TimerService.stopService(self)


class LogWatchingService(LogWatchingBaseService):

    def __init__(self, log_path, interval=1, parser=None):
        LogWatchingBaseService.__init__(self, log_path, interval)
        self.parser = parser or EventLogPassthroughParser()

    def got_line(self, line):
        idx = line.find(']')
        line = line[idx+1:].lstrip().replace('\n', '')
        self.parser.parse_line(line)
