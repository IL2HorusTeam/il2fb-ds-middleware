# coding: utf-8

from collections import namedtuple
from typing import Optional

from il2fb.commons.spatial import Point2D, Point3D
from il2fb.commons.structures import BaseStructure

from .constants import HouseStatus


PreparsedActorPosition = namedtuple(
    'PreparsedActorPosition', ['index', 'data'],
)


class ActorPosition(BaseStructure):

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.to_primitive()})"


class MovingAircraftPosition(ActorPosition):
    __slots__ = ['index', 'id', 'pos', 'is_human', 'member_index', ]

    def __init__(
        self,
        index: int,
        id: str,
        is_human: bool,
        member_index: Optional[int],
        pos: Point3D,
    ):
        self.index = index
        self.id = id
        self.pos = pos
        self.is_human = is_human
        self.member_index = member_index


class MovingGroundUnitPosition(ActorPosition):
    __slots__ = ['index', 'id', 'member_index', 'pos', ]

    def __init__(
        self,
        index: int,
        id: str,
        member_index: int,
        pos: Point3D,
    ):
        self.index = index
        self.id = id
        self.member_index = member_index
        self.pos = pos


class ShipPosition(ActorPosition):
    __slots__ = ['index', 'id', 'pos', 'is_stationary', ]

    def __init__(
        self,
        index: int,
        id: str,
        is_stationary: bool,
        pos: Point2D,
    ):
        self.index = index
        self.id = id
        self.is_stationary = is_stationary
        self.pos = pos


class StationaryObjectPosition(ActorPosition):
    __slots__ = ['index', 'id', 'pos', ]

    def __init__(self, index: int, id: str, pos: Point3D):
        self.index = index
        self.id = id
        self.pos = pos


class HousePosition(ActorPosition):
    __slots__ = ['index', 'id', 'pos', 'status', ]

    def __init__(
        self,
        index: int,
        id: str,
        pos: Point2D,
        status: HouseStatus,
    ):
        self.index = index
        self.id = id
        self.pos = pos
        self.status = status
