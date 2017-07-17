# coding: utf-8

from candv import Values, ValueConstant, with_constant_class


class HouseStatus(ValueConstant):
    pass


class HouseStatuses(with_constant_class(HouseStatus), Values):
    alive = HouseStatus("A")
    dead = HouseStatus("D")


TYPE_REQUEST = 'R'
TYPE_ANSWER = 'A'
TYPE_SEPARATOR = '/'

MESSAGE_SEPARATOR = '/'
MESSAGE_GROUP_MAX_SIZE = 40

VALUE_SEPARATOR = '\\'

ACTOR_INDEX_SEPARATOR = ':'
ACTOR_INDEX_ERROR = 'BADINDEX'
ACTOR_STATUS_ERROR = 'INVALID'
ACTOR_DATA_SEPARATOR = ';'
