# coding: utf-8

import re

from il2fb.commons.spatial import Point2D, Point3D

from . import structures
from .constants import ACTOR_INDEX_SEPARATOR
from .constants import ACTOR_DATA_SEPARATOR
from .constants import STATIC_AIRCRAFT_WITH_HUMAN_SPAWNED_IN
from .constants import HouseStatuses
from .helpers import normalize_aircraft_id


def preparse_actor_position(message: str) -> structures.PreparsedActorPosition:
    index, data = message.split(ACTOR_INDEX_SEPARATOR)
    index = int(index)
    return structures.PreparsedActorPosition(index, data)


def parse_moving_aircraft_position(
    item: structures.PreparsedActorPosition,
) -> structures.MovingAircraftPosition:
    id, x, y, z = item.data.split(ACTOR_DATA_SEPARATOR)
    normalized_id = normalize_aircraft_id(id)
    is_human = (normalized_id != id)
    pos = Point3D(float(x), float(y), float(z))

    if is_human:
        member_index = None
    else:
        normalized_id, member_index = normalized_id[:-1], normalized_id[-1:]
        member_index = int(member_index)

    return structures.MovingAircraftPosition(
        index=item.index,
        id=normalized_id,
        is_human=is_human,
        member_index=member_index,
        pos=pos,
    )


def parse_moving_ground_unit_position(
    item: structures.PreparsedActorPosition,
) -> structures.MovingGroundUnitPosition:
    id, x, y, z = item.data.split(ACTOR_DATA_SEPARATOR)
    id, member_index = re.match(r"(\d+_Chief)(\d+)", id).groups()
    member_index = int(member_index)
    pos = Point3D(float(x), float(y), float(z))
    return structures.MovingGroundUnitPosition(
        index=item.index,
        id=id,
        member_index=member_index,
        pos=pos,
    )


def parse_ship_position(
    item: structures.PreparsedActorPosition,
) -> structures.ShipPosition:
    id, x, y = item.data.split(ACTOR_DATA_SEPARATOR)
    is_stationary = (id.endswith('_Static'))
    pos = Point2D(float(x), float(y))
    return structures.ShipPosition(
        index=item.index,
        id=id,
        is_stationary=is_stationary,
        pos=pos,
    )


def parse_stationary_object_position(
    item: structures.PreparsedActorPosition,
) -> structures.StationaryObjectPosition:

    data = item.data

    if data == STATIC_AIRCRAFT_WITH_HUMAN_SPAWNED_IN:
        return

    id, x, y, z = data.split(ACTOR_DATA_SEPARATOR)
    pos = Point3D(float(x), float(y), float(z))

    return structures.StationaryObjectPosition(
        index=item.index,
        id=id,
        pos=pos,
    )


def parse_house_position(
    item: structures.PreparsedActorPosition,
) -> structures.HousePosition:
    id, x, y, status = item.data.split(ACTOR_DATA_SEPARATOR)
    status = HouseStatuses.get_by_value(status)
    pos = Point2D(float(x), float(y))
    return structures.HousePosition(
        index=item.index,
        id=id,
        pos=pos,
        status=status,
    )
