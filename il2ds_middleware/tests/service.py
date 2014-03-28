# -*- coding: utf-8 -*-
from twisted.application.service import Service
from twisted.internet import defer

from il2ds_middleware import service


class PilotsService(service.MutedPilotsService):

    def __init__(self):
        self.buffer = []

    def append_info(self, info):
        self.buffer.append(info)

    user_joined = user_left = user_chat= seat_occupied = weapons_loaded = \
    was_killed = was_killed_by_user = was_shot_down_by_user = selected_army = \
    went_to_menu = took_off = landed = damaged_self = was_damaged_on_ground = \
    toggle_wingtip_smokes = toggle_landing_lights = crashed = bailed_out = \
    parachute_opened = was_captured = was_wounded = was_heavily_wounded = \
    shot_down_self = was_shot_down_by_static = was_damaged_by_user = \
    append_info


class ObjectsService(service.MutedObjectsService):

    def __init__(self):
        self.buffer = []

    def append_info(self, info):
        self.buffer.append(info)

    building_destroyed_by_user = tree_destroyed_by_user = \
    static_destroyed_by_user = bridge_destroyed_by_user = append_info


class MissionsService(service.MutedMissionsService):

    def __init__(self):
        self.buffer = []

    def append_info(self, info):
        self.buffer.append(info)

    on_status_info = was_won = target_end = append_info


class FakeLogWatchingService(Service):

    def stopService(self):
        Service.stopService(self)
        return defer.succeed(None)
