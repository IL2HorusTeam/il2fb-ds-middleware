# coding: utf-8

import asyncio
import concurrent
import functools
import logging
import operator

from typing import List, Awaitable, Callable, Any, Optional, Iterable

from . import messages as msg, parsers
from .constants import MESSAGE_GROUP_MAX_SIZE
from .filters import actor_index_is_valid, actor_status_is_valid
from .helpers import compose_request, decompose_data


LOG = logging.getLogger(__name__)


class DeviceLinkRequest:

    def __init__(
        self,
        messages: List[msg.DeviceLinkRequestMessage],
        loop: asyncio.AbstractEventLoop=None,
        timeout: float=None,
    ):
        self._loop = loop
        self._request_messages = messages
        self._timeout = timeout
        self._response_messages = []
        self._future = asyncio.Future(loop=loop)

    def wait(self) -> Awaitable[Any]:
        return self._future

    def execute(self, writer: Callable[[bytes], None]) -> Awaitable[Any]:
        messages = self._request_messages

        for group in self._group_messages(messages):
            data = compose_request(group)
            writer(data)

        future = self._future
        requires_response = any(msg.requires_response for msg in messages)

        if requires_response and self._timeout:
            future = self._execute_with_timeout(future, timeout=self._timeout)
        else:
            future.set_result(None)

        return future

    async def _execute_with_timeout(
        self,
        future: asyncio.Future,
        timeout: float,
    ) -> asyncio.Future:

        timeout_future = asyncio.Future(loop=self._loop)
        future.add_done_callback(functools.partial(
            self._on_future_done, timeout_future,
        ))

        try:
            await asyncio.wait_for(timeout_future, timeout, loop=self._loop)
        except concurrent.futures.TimeoutError as e:
            self._future.set_exception(e)

    @staticmethod
    def _on_future_done(
        timeout_future: asyncio.Future,
        wrapped_future: asyncio.Future,
    ) -> None:

        if not timeout_future.done():
            timeout_future.set_result(None)

    def _group_messages(self, messages, group_size=MESSAGE_GROUP_MAX_SIZE):
        count = len(messages)

        for i in range((count // group_size) + 1):
            start = i * group_size
            yield messages[start:start + min((count - start), group_size)]

    def data_received(self, data: bytes) -> None:
        try:
            messages = decompose_data(data)
        except Exception:
            LOG.exception(f"failed to decompose data {repr(data)}")
        else:
            LOG.debug(f"msg <<< {messages}")

        self._response_messages.extend(messages)
        LOG.debug(f"msg === {self._response_messages}")

        if len(self._response_messages) == len(self._request_messages):
            try:
                result = self._extract_result(self._response_messages)
            except Exception as e:
                LOG.exception("failed to get request result")
                self._future.set_exception(result)
            else:
                self._future.set_result(result)

    def set_exception(self, e: Exception=None) -> None:
        if not self._future.done():
            self._future.set_exception(e)

    def _extract_result(self, messages: List[msg.DeviceLinkMessage]) -> Any:
        return messages

    def __str__(self) -> str:
        return compose_request(self._request_messages).decode()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{str(self)}')>"


class CountingRequestMixin:

    @property
    def request_message_class(self):
        raise NotImplementedError

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop=None,
        timeout: Optional[float]=None,
    ):
        messages = [
            self.request_message_class(),
        ]
        super().__init__(
            loop=loop,
            messages=messages,
            timeout=timeout,
        )

    def _extract_result(self, messages: List[msg.DeviceLinkMessage]) -> None:
        message = messages[0]
        return int(message.value)


class PositionsRequestMixin:

    @property
    def request_message_class(self):
        raise NotImplementedError

    @property
    def item_parser(self):
        raise NotImplementedError

    def __init__(
        self,
        indices: Iterable[int],
        loop: asyncio.AbstractEventLoop=None,
        timeout: Optional[float]=None,
    ):
        messages = [
            self.request_message_class(value=i) for i in indices
        ]
        super().__init__(
            loop=loop,
            messages=messages,
            timeout=timeout,
        )

    def _extract_result(self, messages: List[msg.DeviceLinkMessage]) -> None:
        items = map(operator.attrgetter('value'), messages)
        items = map(parsers.preparse_actor_position, items)
        items = filter(actor_index_is_valid, items)
        items = filter(actor_status_is_valid, items)
        items = map(self.__class__.item_parser, items)
        return list(items)


class RefreshRadarRequest(DeviceLinkRequest):

    def __init__(self, loop: asyncio.AbstractEventLoop=None):
        messages = [
            msg.RefreshRadarRequestMessage(),
        ]
        super().__init__(
            loop=loop,
            messages=messages,
            timeout=None,
        )


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
