# coding: utf-8

import asyncio
import logging
import operator
import time

from typing import List, Awaitable, Callable, Any, Optional, Iterable

from il2fb.ds.middleware.device_link import messages as msg
from il2fb.ds.middleware.device_link import parsers
from il2fb.ds.middleware.device_link.constants import MESSAGE_GROUP_MAX_SIZE
from il2fb.ds.middleware.device_link.filters import actor_index_is_valid
from il2fb.ds.middleware.device_link.filters import actor_status_is_valid
from il2fb.ds.middleware.device_link.helpers import compose_request
from il2fb.ds.middleware.device_link.helpers import decompose_data
from il2fb.ds.middleware.text import plural_noun, truncate


LOG = logging.getLogger(__name__)


class DeviceLinkRequest:

    def __init__(
        self,
        messages: List[msg.DeviceLinkRequestMessage],
        timeout: float=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        self._loop = loop
        self._trace = trace

        self._request_messages = messages
        self._request_requires_response = self._messages_require_response(
            messages=messages,
        )

        self._response_messages = []
        self._future = asyncio.Future(loop=loop)

        self._start_time = None
        self._timeout = timeout

        self._continue_event = asyncio.Event(loop=loop)
        self._continue_event.set()

    def result(self) -> Awaitable[Any]:
        return self._future

    async def execute(
        self,
        writer: Callable[[bytes], None],
    ) -> Awaitable[None]:

        LOG.debug("device link request execution start")

        try:
            future = self._execute(writer)

            if self._timeout and self._request_requires_response:
                future = asyncio.wait_for(
                    future,
                    self._timeout,
                    loop=self._loop,
                )

            await future
        except Exception as e:
            if self._future.done():
                LOG.exception("failed to execute device link request")
            else:
                self._future.set_exception(e)
        finally:
            execution_time = time.monotonic() - self._start_time
            LOG.debug(
                "device link request execution time: {:.6f} s"
                .format(execution_time)
            )

    async def _execute(
        self,
        writer: Callable[[bytes], None],
    ) -> Awaitable[None]:
        self._start_time = time.monotonic()

        messages = self._request_messages
        messages_total_count = len(messages)
        messages_sent_count = 0

        for group in self._group_messages(messages):
            data = compose_request(group)
            group_requires_response = self._messages_require_response(group)

            future = self._continue_event.wait()

            if group_requires_response:
                self._continue_event.clear()
                writer(data)
                future = self._maybe_wrap_with_timeout(future)
            else:
                writer(data)

            # gives ability to switch context to other coroutines
            await future

            if self._future.done():
                break

            messages_sent_count += len(group)

            LOG.debug(
                f"msg count: {messages_sent_count} out of "
                f"{messages_total_count}"
            )

        if self._future.done():
            LOG.debug("device link request was aborted")
        elif self._request_requires_response:
            result = self._extract_result(self._response_messages)
            self._future.set_result(result)
        else:
            self._future.set_result(None)

    @staticmethod
    def _messages_require_response(
        messages: List[msg.DeviceLinkRequestMessage],
    ) -> bool:
        return any(msg.requires_response for msg in messages)

    def _maybe_wrap_with_timeout(
        self,
        future: asyncio.Future,
    ) -> asyncio.Future:

        if self._timeout:
            elapsed_time = time.monotonic() - self._start_time

            if elapsed_time >= self._timeout:
                raise TimeoutError

            timeout = self._timeout - elapsed_time
            future = asyncio.wait_for(future, timeout, loop=self._loop)

        return future

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
            self._response_messages.extend(messages)

            if self._trace:
                s = truncate(str(messages), max_length=200)
                count = len(messages)
                message_noun = plural_noun("message", count)
                LOG.debug(f"msg <<< {s}, {count} {message_noun}")

        self._continue_event.set()

    def set_exception(self, e: Exception=None) -> None:
        if not self._future.done():
            self._future.set_exception(e)

    def _extract_result(self, messages: List[msg.DeviceLinkMessage]) -> Any:
        return messages

    def __str__(self) -> str:
        s = compose_request(self._request_messages).decode()
        return truncate(s, max_length=200)

    def __repr__(self) -> str:
        value = str(self)
        count = len(self._request_messages)
        message_noun = plural_noun("message", count)
        return (
            f"<{self.__class__.__name__} "
            f"(data='{value}', {count} {message_noun})>"
        )


class CountingRequestMixin:

    @property
    def request_message_class(self):
        raise NotImplementedError

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop=None,
        timeout: Optional[float]=None,
        trace: bool=False,
    ):
        messages = [
            self.request_message_class(),
        ]
        super().__init__(
            loop=loop,
            messages=messages,
            timeout=timeout,
            trace=trace,
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
        trace: bool=False,
    ):
        messages = [
            self.request_message_class(value=i) for i in indices
        ]
        super().__init__(
            loop=loop,
            messages=messages,
            timeout=timeout,
            trace=trace,
        )

    def _extract_result(self, messages: List[msg.DeviceLinkMessage]) -> None:
        items = map(operator.attrgetter('value'), messages)
        items = map(parsers.preparse_actor_position, items)
        items = filter(actor_index_is_valid, items)
        items = filter(actor_status_is_valid, items)
        items = map(self.__class__.item_parser, items)
        items = filter(bool, items)
        return list(items)


class RefreshRadarRequest(DeviceLinkRequest):

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop=None,
        trace: bool=False,
    ):
        messages = [
            msg.RefreshRadarRequestMessage(),
        ]
        super().__init__(
            loop=loop,
            messages=messages,
            timeout=None,
            trace=trace,
        )


class GetMovingAircraftsCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.MovingAircraftsCountRequestMessage


class GetMovingAircraftsPositionsRequest(
    PositionsRequestMixin,
    DeviceLinkRequest,
):
    request_message_class = msg.MovingAircraftPositionRequestMessage
    item_parser = parsers.parse_moving_aircraft_position


class GetMovingGroundUnitsCountRequest(
    CountingRequestMixin,
    DeviceLinkRequest,
):
    request_message_class = msg.MovingGroundUnitsCountRequestMessage


class GetMovingGroundUnitsPositionsRequest(
    PositionsRequestMixin,
    DeviceLinkRequest,
):
    request_message_class = msg.MovingGroundUnitPositionRequestMessage
    item_parser = parsers.parse_moving_ground_unit_position


class GetShipsCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.ShipsCountRequestMessage


class GetShipsPositionsRequest(PositionsRequestMixin, DeviceLinkRequest):
    request_message_class = msg.ShipPositionRequestMessage
    item_parser = parsers.parse_ship_position


class GetStationaryObjectsCountRequest(
    CountingRequestMixin,
    DeviceLinkRequest,
):
    request_message_class = msg.StationaryObjectsCountRequestMessage


class GetStationaryObjectsPositionsRequest(
    PositionsRequestMixin,
    DeviceLinkRequest,
):
    request_message_class = msg.StationaryObjectPositionRequestMessage
    item_parser = parsers.parse_stationary_object_position


class GetHousesCountRequest(CountingRequestMixin, DeviceLinkRequest):
    request_message_class = msg.HousesCountRequestMessage


class GetHousesPositionsRequest(PositionsRequestMixin, DeviceLinkRequest):
    request_message_class = msg.HousePositionRequestMessage
    item_parser = parsers.parse_house_position
