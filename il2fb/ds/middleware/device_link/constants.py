# coding: utf-8

from candv import Values, ValueConstant, with_constant_class


class HouseStatus(ValueConstant):
    pass


class HouseStatuses(with_constant_class(HouseStatus), Values):
    alive = HouseStatus("A")
    dead = HouseStatus("D")


MESSAGE_TYPE_SEPARATOR = b'/'
MESSAGE_SEPARATOR = b'/'
MESSAGE_GROUP_MAX_SIZE = 40

REQUEST_PREFIX = b'R' + MESSAGE_TYPE_SEPARATOR
ANSWER_PREFIX = b'A' + MESSAGE_TYPE_SEPARATOR

VALUE_SEPARATOR = b'\\'

ACTOR_INDEX_SEPARATOR = ':'
ACTOR_INDEX_ERROR = 'BADINDEX'
ACTOR_STATUS_ERROR = 'INVALID'
ACTOR_DATA_SEPARATOR = ';'

STATIC_AIRCRAFT_WITH_HUMAN_SPAWNED_IN = 'INAIR'
