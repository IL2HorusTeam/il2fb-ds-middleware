# -*- coding: utf-8 -*-

from il2ds_middleware.service import PilotBaseService


class PilotService(PilotBaseService):

    def __init__(self, parser=None):
        PilotBaseService.__init__(self, parser)
        self.joined = []
        self.left = []

    def user_join(self, info):
        self.joined.append(info)

    def user_left(self, info):
        self.left.append(info)
