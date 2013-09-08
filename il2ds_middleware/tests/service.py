# -*- coding: utf-8 -*-

from twisted.application.service import Service
from twisted.internet import defer

from il2ds_middleware import service


class PilotService(service.PilotBaseService):

    def __init__(self):
        self.buffer = []

    def append_info(self, info):
        self.buffer.append(info)

    append_info = user_join = user_left = user_chat= \
    seat_occupied = weapons_loaded = was_killed = \
    was_shot_down = selected_army = went_to_menu = was_destroyed = \
    in_flight = landed = damaged = damaged_on_ground = \
    turned_wingtip_smokes = crashed = bailed_out = was_captured = \
    was_captured = was_wounded = was_heavily_wounded = removed = append_info


class ObjectsService(service.ObjectsBaseService):

    def __init__(self):
        self.buffer = []

    def was_destroyed(self, info):
        self.buffer.append(info)


class MissionService(service.MissionBaseService):

    def __init__(self):
        self.buffer = []

    def on_status_info(self, info):
        self.buffer.append(info)


class FakeLogWatchingService(Service):

    def stopService(self):
        Service.stopService(self)
        return defer.succeed(None)
