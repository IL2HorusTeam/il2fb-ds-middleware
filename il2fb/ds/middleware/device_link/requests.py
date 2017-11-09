# coding: utf-8

import asyncio
import logging
import operator
import time

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
        self._timeout = timeout
        self._request_messages = messages
        self._response_messages = []
        self._continue_event = asyncio.Event(loop=loop)
        self._future = asyncio.Future(loop=loop)

    def wait(self) -> Awaitable[Any]:
        return self._future

    async def execute(
        self,
        writer: Callable[[bytes], None],
    ) -> Awaitable[Any]:
        try:
            await self._execute(writer)
        except Exception as e:
            if self._future.done():
                LOG.exception("failed to execute device link request")
            else:
                self._future.set_exception(e)

    async def _execute(
        self,
        writer: Callable[[bytes], None],
    ) -> Awaitable[Any]:
        start_time = time.monotonic()

        messages = self._request_messages
        messages_total_count = len(messages)
        messages_sent_count = 0

        request_requires_response = False

        for group in self._group_messages(messages):
            data = compose_request(group)

            group_requires_response = any(
                msg.requires_response for msg in group
            )
            request_requires_response = (
                request_requires_response or
                group_requires_response
            )

            elapsed_time = time.monotonic() - start_time
            if self._timeout is not None and elapsed_time >= self._timeout:
                raise TimeoutError

            if group_requires_response:
                self._continue_event.clear()
                writer(data)

                future = self._continue_event.wait()

                if self._timeout is not None:
                    timeout = self._timeout - elapsed_time
                    future = asyncio.wait_for(future, timeout, loop=self._loop)

                await future
            else:
                writer(data)

            messages_sent_count += len(group)
            LOG.debug(
                f"msg count: {messages_sent_count} out of "
                f"{messages_total_count}"
            )

        if request_requires_response:
            result = self._extract_result(self._response_messages)
            self._future.set_result(result)
        else:
            self._future.set_result(None)

    @staticmethod
    def _group_messages(messages, group_size=MESSAGE_GROUP_MAX_SIZE):
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

        self._continue_event.set()

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


class MovingAircraftsCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.MovingAircraftsCountRequestMessage


class MovingAircraftsPositionsRequest(
    PositionsRequestMixin,
    DeviceLinkRequest,
):
    request_message_class = msg.MovingAircraftPositionRequestMessage
    item_parser = parsers.parse_moving_aircraft_position


class MovingGroundUnitsCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.MovingGroundUnitsCountRequestMessage


class MovingGroundUnitsPositionsRequest(
    PositionsRequestMixin,
    DeviceLinkRequest,
):
    request_message_class = msg.MovingGroundUnitPositionRequestMessage
    item_parser = parsers.parse_moving_ground_unit_position


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
