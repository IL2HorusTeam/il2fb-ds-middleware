# coding: utf-8

from typing import Optional

from .constants import VALUE_SEPARATOR


class DeviceLinkMessage:
    __slots__ = ['opcode', 'value', ]

    def __init__(self, opcode: int, value: Optional[int]=None):
        self.opcode = opcode
        self.value = value

    def __str__(self) -> str:
        return (
            f"{self.opcode}{VALUE_SEPARATOR}{self.value}"
            if self.value is not None
            else str(self.opcode)
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{str(self)}')>"


class RefreshRadarRequestMessage(DeviceLinkMessage):

    def __init__(self):
        super().__init__(opcode=1001)


class AircraftsCountRequestMessage(DeviceLinkMessage):

    def __init__(self):
        super().__init__(opcode=1002)


class AircraftPositionRequestMessage(DeviceLinkMessage):

    def __init__(self, index: int):
        super().__init__(opcode=1004, value=index)


class GroundUnitsCountRequestMessage(DeviceLinkMessage):

    def __init__(self):
        super().__init__(opcode=1006)


class GroundUnitPositionRequestMessage(DeviceLinkMessage):

    def __init__(self, index: int):
        super().__init__(opcode=1008, value=index)


class ShipsCountRequestMessage(DeviceLinkMessage):

    def __init__(self):
        super().__init__(opcode=1010)


class ShipPositionRequestMessage(DeviceLinkMessage):

    def __init__(self, index: int):
        super().__init__(opcode=1012, value=index)


class StationaryObjectsCountRequestMessage(DeviceLinkMessage):

    def __init__(self):
        super().__init__(opcode=1014)


class StationaryObjectPositionRequestMessage(DeviceLinkMessage):

    def __init__(self, index: int):
        super().__init__(opcode=1016, value=index)


class HousesCountRequestMessage(DeviceLinkMessage):

    def __init__(self):
        super().__init__(opcode=1018)


class HousePositionRequestMessage(DeviceLinkMessage):

    def __init__(self, index: int):
        super().__init__(opcode=1020, value=index)
