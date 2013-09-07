# -*- coding: utf-8 -*-

from zope.interface import Interface


class IPilotService(Interface):

    def user_join(self, info):
        """
        """

    def user_left(self, info):
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

    def user_chat(self, info):
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
