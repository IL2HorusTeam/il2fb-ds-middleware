# -*- coding: utf-8 -*-

from zope.interface import Interface


class IPilotService(Interface):

    def user_join(self, info):
        """
        """

    def user_left(self, info):
        """
        """

    def user_chat(self, info):
        """
        """

    def seat_occupied(self, info):
        """
        """

    def weapons_loaded(self, info):
        """
        """

    def was_killed(self, info):
        """
        """

    def was_shot_down(self, info):
        """
        """

    def selected_army(self, info):
        """
        """

    def went_to_menu(self, info):
        """
        """

    def was_destroyed(self, info):
        """
        """

    def in_flight(self, info):
        """
        """

    def landed(self, info):
        """
        """

    def damaged(self, info):
        """
        """

    def damaged_on_ground(self, info):
        """
        """

    def turned_wingtip_smokes(self, info):
        """
        """

    def crashed(self, info):
        """
        """

    def bailed_out(self, info):
        """
        """

    def was_captured(self, info):
        """
        """

    def was_wounded(self, info):
        """
        """

    def was_heavily_wounded(self, info):
        """
        """

    def removed(self, info):
        """
        """


class IObjectsService(Interface):

    def was_destroyed(self, info):
        """
        """


class IMissionService(Interface):


    def on_status_info(self, info):
        """
        """

    def began(self, info=None):
        """
        """

    def ended(self, info=None):
        """
        """
