# coding: utf-8

from typing import Optional, Any, TypeVar

from .constants import VALUE_SEPARATOR


_OPCODE_TO_MESSAGE_CLASS = {}


class DeviceLinkMessageMeta(type):

    def __init__(cls, name, bases, nmspc):
        super(DeviceLinkMessageMeta, cls).__init__(name, bases, nmspc)

        if hasattr(cls, 'opcode') and cls.opcode is not None:
            _OPCODE_TO_MESSAGE_CLASS[cls.opcode] = cls


class DeviceLinkMessage(metaclass=DeviceLinkMessageMeta):
    opcode = None

    def __init__(self, opcode: Optional[int]=None, value: Optional[Any]=None):
        self.opcode = (
            opcode
            if opcode is not None
            else self.opcode
        )
        self.value = value

    def to_bytes(self) -> bytes:
        data = str(self.opcode).encode()

        if self.value is not None:
            data += VALUE_SEPARATOR + str(self.value).encode()

        return data

    def __repr__(self) -> str:
        return (
            f"<"
            f"{self.__class__.__name__}"
            f"(opcode={self.opcode}, value={self.value})"
            f">"
        )


def get_message_class_by_opcode(
    opcode: int
) -> Optional[TypeVar(DeviceLinkMessage)]:
    return _OPCODE_TO_MESSAGE_CLASS.get(opcode)


def make_message(opcode: int, value: Optional[Any]=None) -> DeviceLinkMessage:
    cls = get_message_class_by_opcode(opcode)

    if cls is not None:
        return cls(value=value)

    return DeviceLinkMessage(opcode=opcode, value=value)


class DeviceLinkRequestMessage(DeviceLinkMessage):

    @property
    def requires_response(self) -> bool:
        raise NotImplementedError


class RefreshRadarRequestMessage(DeviceLinkRequestMessage):
    opcode = 1001
    requires_response = False


class DeviceLinkGetterRequestMessage(DeviceLinkRequestMessage):
    requires_response = True


class MovingAircraftsCountRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1002


class MovingAircraftPositionRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1004


class MovingGroundUnitsCountRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1006


class MovingGroundUnitPositionRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1008


class ShipsCountRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1010


class ShipPositionRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1012


class StationaryObjectsCountRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1014


class StationaryObjectPositionRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1016


class HousesCountRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1018


class HousePositionRequestMessage(DeviceLinkGetterRequestMessage):
    opcode = 1020
