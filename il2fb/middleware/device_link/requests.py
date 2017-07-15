# coding: utf-8

import abc
import asyncio
import logging
import operator

from typing import List, Callable, Any, Optional, Iterable

from . import messages as msg, parsers
from .filters import actor_index_is_valid, actor_status_is_valid
from .helpers import compose_request


LOG = logging.getLogger(__name__)


class DeviceLinkRequest:
    __slots__ = ['messages', 'timeout', '_future', ]

    def __init__(
        self,
        future: asyncio.Future,
        messages: List[msg.DeviceLinkMessage],
        timeout: Optional[float],
    ):
        self._future = future
        self.messages = messages
        self.timeout = timeout

    def set_result(self, result: Any) -> None:
        try:
            self._future.set_result(result)
        except asyncio.futures.InvalidStateError:
            LOG.error(
                f"failed to set request result "
                f"(request={self}, future={self.future}, result={result})"
            )

    def set_exception(self, e: Exception) -> None:
        try:
            self._future.set_exception(e)
        except asyncio.futures.InvalidStateError:
            LOG.error(
                f"failed to set request exception "
                f"(request={self}, future={self.future}, e={e})"
            )

    def add_done_callback(self, cb: Callable[[asyncio.Future], None]) -> None:
        self._future.add_done_callback(cb)

    def __str__(self) -> str:
        return compose_request(self.messages)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{str(self)}')>"


class CountingRequestMixin(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def request_message_class(self):
        pass

    def __init__(
        self,
        future: asyncio.Future,
        timeout: Optional[float],
    ):
        messages = [self.request_message_class(), ]
        super().__init__(future, messages, timeout)

    def set_result(self, messages: List[msg.DeviceLinkMessage]) -> None:
        message = messages[0]
        value = int(message.value)
        super().set_result(value)


class PositionsRequestMixin(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def request_message_class(self):
        pass

    @property
    @abc.abstractmethod
    def item_parser(self):
        pass

    def __init__(
        self,
        future: asyncio.Future,
        indices: Iterable[int],
        timeout: Optional[float],
    ):
        messages = [
            self.request_message_class(i) for i in indices
        ]
        super().__init__(future, messages, timeout)

    def set_result(self, messages: List[msg.DeviceLinkMessage]) -> None:
        items = map(operator.attrgetter('value'), messages)
        items = map(parsers.preparse_actor_position, items)
        items = filter(actor_index_is_valid, items)
        items = filter(actor_status_is_valid, items)
        items = map(self.__class__.item_parser, items)
        items = list(items)
        super().set_result(items)


class AircraftsCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.AircraftsCountRequestMessage


class AircraftsPositionsRequest(PositionsRequestMixin, DeviceLinkRequest):
    request_message_class = msg.AircraftPositionRequestMessage
    item_parser = parsers.parse_aircraft_position


class GroundUnitsCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.GroundUnitsCountRequestMessage


class GroundUnitsPositionsRequest(PositionsRequestMixin, DeviceLinkRequest):
    request_message_class = msg.GroundUnitPositionRequestMessage
    item_parser = parsers.parse_ground_unit_position


class ShipsCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.ShipsCountRequestMessage


class ShipsPositionsRequest(PositionsRequestMixin, DeviceLinkRequest):
    request_message_class = msg.ShipPositionRequestMessage
    item_parser = parsers.parse_ship_position


class StationaryObjectsCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.StationaryObjectsCountRequestMessage


class StationaryObjectsPositionsRequest(
    PositionsRequestMixin,
    DeviceLinkRequest,
):
    request_message_class = msg.StationaryObjectPositionRequestMessage
    item_parser = parsers.parse_stationary_object_position


class HousesCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.HousesCountRequestMessage


class HousesPositionsRequest(PositionsRequestMixin, DeviceLinkRequest):
    request_message_class = msg.HousePositionRequestMessage
    item_parser = parsers.parse_house_position
