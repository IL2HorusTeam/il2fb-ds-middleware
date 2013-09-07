# -*- coding: utf-8 -*-

from il2ds_middleware.service import (PilotBaseService, ObjectsBaseService,
    MissionBaseService, )


class PilotService(PilotBaseService):

    def __init__(self):
        self.joined = []
        self.left = []
        self.occupied = []
        self.weapons = []
        self.killed = []
        self.shot_down = []
        self.army_select = []
        self.to_menu = []
        self.chat = []

    def user_join(self, info):
        self.joined.append(info)

    def user_left(self, info):
        self.left.append(info)

    def seat_occupied(self, info):
        self.occupied.append(info)

    def weapons_loaded(self, info):
        self.weapons.append(info)

    def was_killed(self, info):
        self.killed.append(info)

    def was_shot_down(self, info):
        self.shot_down.append(info)

    def selected_army(self, info):
        self.army_select.append(info)

    def went_to_menu(self, info):
        self.to_menu.append(info)

    def user_chat(self, info):
        self.chat.append(info)


class ObjectsService(ObjectsBaseService):

    def __init__(self):
        self.destroyed = []

    def was_destroyed(self, info):
        self.destroyed.append(info)
