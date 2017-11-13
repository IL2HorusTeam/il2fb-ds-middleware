# coding: utf-8

from typing import Optional

from il2fb.commons import MissionStatus
from il2fb.commons.organization import Belligerent
from il2fb.commons.structures import BaseStructure


class ServerInfo(BaseStructure):
    __slots__ = ['type', 'name', 'description', ]

    def __init__(self, type: str, name: str, description: str):
        self.type = type
        self.name = name
        self.description = description


class Aircraft(BaseStructure):
    __slots__ = ['designation', 'type', ]

    def __init__(self, designation: str, type: str):
        self.designation = designation
        self.type = type


class Human(BaseStructure):
    __slots__ = ['callsign', 'ping', 'score', 'belligerent', 'aircraft', ]

    def __init__(
        self,
        callsign: str,
        ping: int,
        score: int,
        belligerent: Optional[Belligerent],
        aircraft: Optional[Aircraft],
    ):
        self.callsign = callsign
        self.ping = ping
        self.score = score
        self.belligerent = belligerent
        self.aircraft = aircraft


class HumanStatistics(BaseStructure):
    __slots__ = [
        'callsign',
        'score',
        'state',

        'enemy_aircraft_kills',
        'enemy_static_aircraft_kills',
        'enemy_tank_kills',
        'enemy_car_kills',
        'enemy_artillery_kills',
        'enemy_aaa_kills',
        'enemy_wagon_kills',
        'enemy_ship_kills',
        'enemy_radio_kills',

        'friendly_aircraft_kills',
        'friendly_static_aircraft_kills',
        'friendly_tank_kills',
        'friendly_car_kills',
        'friendly_artillery_kills',
        'friendly_aaa_kills',
        'friendly_wagon_kills',
        'friendly_ship_kills',
        'friendly_radio_kills',

        'bullets_fired',
        'bullets_hit',
        'bullets_hit_air_targets',

        'rockets_launched',
        'rockets_hit',

        'bombs_dropped',
        'bombs_hit',
    ]

    def __init__(
        self,

        callsign: str,
        score: int,
        state: str,

        enemy_aircraft_kills: int,
        enemy_static_aircraft_kills: int,
        enemy_tank_kills: int,
        enemy_car_kills: int,
        enemy_artillery_kills: int,
        enemy_aaa_kills: int,
        enemy_wagon_kills: int,
        enemy_ship_kills: int,
        enemy_radio_kills: int,

        friendly_aircraft_kills: int,
        friendly_static_aircraft_kills: int,
        friendly_tank_kills: int,
        friendly_car_kills: int,
        friendly_artillery_kills: int,
        friendly_aaa_kills: int,
        friendly_wagon_kills: int,
        friendly_ship_kills: int,
        friendly_radio_kills: int,

        bullets_fired: int,
        bullets_hit: int,
        bullets_hit_air_targets: int,

        rockets_launched: int,
        rockets_hit: int,

        bombs_dropped: int,
        bombs_hit: int,
    ):
        self.callsign = callsign
        self.score = score
        self.state = state

        self.enemy_aircraft_kills = enemy_aircraft_kills
        self.enemy_static_aircraft_kills = enemy_static_aircraft_kills
        self.enemy_tank_kills = enemy_tank_kills
        self.enemy_car_kills = enemy_car_kills
        self.enemy_artillery_kills = enemy_artillery_kills
        self.enemy_aaa_kills = enemy_aaa_kills
        self.enemy_wagon_kills = enemy_wagon_kills
        self.enemy_ship_kills = enemy_ship_kills
        self.enemy_radio_kills = enemy_radio_kills

        self.friendly_aircraft_kills = friendly_aircraft_kills
        self.friendly_static_aircraft_kills = friendly_static_aircraft_kills
        self.friendly_tank_kills = friendly_tank_kills
        self.friendly_car_kills = friendly_car_kills
        self.friendly_artillery_kills = friendly_artillery_kills
        self.friendly_aaa_kills = friendly_aaa_kills
        self.friendly_wagon_kills = friendly_wagon_kills
        self.friendly_ship_kills = friendly_ship_kills
        self.friendly_radio_kills = friendly_radio_kills

        self.bullets_fired = bullets_fired
        self.bullets_hit = bullets_hit
        self.bullets_hit_air_targets = bullets_hit_air_targets

        self.rockets_launched = rockets_launched
        self.rockets_hit = rockets_hit

        self.bombs_dropped = bombs_dropped
        self.bombs_hit = bombs_hit


class MissionInfo(BaseStructure):
    __slots__ = ['status', 'file_path', ]

    def __init__(self, status: MissionStatus, file_path: Optional[str]):
        self.status = status
        self.file_path = file_path
