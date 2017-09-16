# coding: utf-8

import asyncio
import concurrent
import functools
import logging

from typing import List, Tuple, Awaitable, Callable, Any

from . import messages as msg, structures, requests
from .constants import TYPE_ANSWER, MESSAGE_GROUP_MAX_SIZE
from .helpers import compose_request, decompose_response


LOG = logging.getLogger(__name__)

Address = Tuple[str, int]


class DeviceLinkClient(asyncio.DatagramProtocol):

    def __init__(
        self,
        remote_address: Address,
        request_timeout: float=20.0,
        on_data_received: Callable[[bytes], bool]=None,
    ):
        self._remote_address = remote_address
        self._request_timeout = request_timeout
        self._requests = asyncio.Queue()
        self._request = None

        self._on_data_received = on_data_received

        self._transport = None
        self._messages = []

        self._do_close = False
        self._connected_ack = asyncio.Future()
        self._closed_ack = asyncio.Future()

    def connection_made(self, transport) -> None:
        self._transport = transport
        asyncio.async(self._dispatch_all_requests())
        self._connected_ack.set_result(None)

    def wait_connected(self) -> Awaitable[None]:
        return self._connected_ack

    def write_bytes(self, data: bytes) -> None:
        self._transport.sendto(data)
        LOG.debug(f"dat --> {repr(data)}")

    async def _dispatch_all_requests(self) -> None:
        LOG.info("dispatching of device link requests has started")

        while True:
            try:
                await self._dispatch_request()
            except StopAsyncIteration:
                break
            except Exception:
                LOG.exception(
                    "failed to dispatch a single device link request"
                )

        LOG.info("dispatching of device link requests has stopped")

        self._transport.close()

        if not self._closed_ack.done():
            self._closed_ack.set_result(None)

    async def _dispatch_request(self) -> None:
        self._request = await self._requests.get()

        if not self._request or self._do_close:
            LOG.info("got request to stop dispatching device link requests")
            raise StopAsyncIteration

        LOG.debug(f"req <-- {repr(self._request)}")

        messages = self._request.messages
        step = MESSAGE_GROUP_MAX_SIZE
        count = len(messages)

        for i in range((count // step) + 1):
            start = i * step
            group = messages[start:start + min((count - start), step)]
            data = compose_request(group).encode()
            self.write_bytes(data)

        try:
            if self._request.timeout is None:
                self._request.set_result(None)
            else:
                await self._wait_for_response()
        finally:
            if self._messages:
                self._messages = []

            self._request = None

    async def _wait_for_response(self) -> Awaitable[None]:
        timeout_future = asyncio.Future()
        self._request.add_done_callback(functools.partial(
            self._on_wrapped_future_done, timeout_future,
        ))

        try:
            await asyncio.wait_for(timeout_future, self._request.timeout)
        except concurrent.futures.TimeoutError as e:
            self._request.set_exception(e)

    @staticmethod
    def _on_wrapped_future_done(
        timeout_future: asyncio.Future,
        wrapped_future: asyncio.Future,
    ) -> None:
        if not timeout_future.done():
            timeout_future.set_result(None)

    def datagram_received(self, data: bytes, addr: Address) -> None:
        if addr != self._remote_address:
            LOG.warning(f"dat <-? unknown sender {addr}, skip")
            return

        LOG.debug(f"dat <-- {repr(data)}")

        if self._on_data_received:
            is_trapped = self._on_data_received(data)
            if is_trapped:
                return

        if not self._request:
            LOG.warning(f"req N/A, skip")
            return

        response = data.decode()
        if not response.startswith(TYPE_ANSWER):
            LOG.error(f"msg <-! malformed response {repr(response)}")
            return

        try:
            messages = decompose_response(response)
        except Exception as e:
            LOG.exception(f"failed to decompose {repr(response)}")
            return
        else:
            LOG.debug(f"msg <<< {messages}")

        self._messages.extend(messages)
        LOG.debug(f"msg === {self._messages}")

        if len(self._messages) == len(self._request.messages):
            messages, self._messages = self._messages, []
            LOG.debug(f"res {messages}")

            try:
                self._request.set_result(messages)
            except Exception as e:
                LOG.exception("failed to set result of request")
                try:
                    self._request.set_exception(e)
                except Exception:
                    LOG.exception("failed to set exception of request")

    def error_received(self, e) -> None:
        LOG.error(f"err <-- {e}")
        if self._request:
            self._request.set_exception(e)

    def send_message(
        self,
        message: msg.DeviceLinkMessage,
        timeout: float,
    ) -> Awaitable[Any]:
        return self.send_messages(messages=[message, ], timeout=timeout)

    def send_messages(
        self,
        messages: List[msg.DeviceLinkMessage],
        timeout: float,
    ) -> Awaitable[Any]:
        f = asyncio.Future()
        r = requests.DeviceLinkRequest(f, messages, timeout)
        self.enqueue_request(r)
        return f

    def enqueue_request(self, request: requests.DeviceLinkRequest) -> None:
        if self._do_close:
            raise ConnectionAbortedError(
                "client is closed and does not accept requests"
            )

        self._requests.put_nowait(request)

    def close(self) -> None:
        if not self._do_close:
            self._do_close = True
            self._requests.put_nowait(None)

    def wait_closed(self) -> Awaitable[None]:
        return self._closed_ack

    def refresh_radar(self) -> Awaitable[None]:
        m = msg.RefreshRadarRequestMessage()
        return self.send_message(message=m, timeout=None)

    def aircrafts_count(self) -> Awaitable[int]:
        f = asyncio.Future()
        r = requests.AircraftsCountRequest(f, self._request_timeout)
        self.enqueue_request(r)
        return f

    def aircraft_position(
        self,
        index: int,
    ) -> Awaitable[structures.AircraftPosition]:
        f = asyncio.Future()
        r = requests.AircraftsPositionsRequest(
            future=f,
            indices=[index, ],
            timeout=self._request_timeout,
        )
        self.enqueue_request(r)
        return f

    async def all_aircrafts_positions(
        self,
    ) -> Awaitable[List[structures.AircraftPosition]]:
        count = await self.aircrafts_count()

        if not count:
            return []

        f = asyncio.Future()
        indices = range(count)
        r = requests.AircraftsPositionsRequest(
            future=f,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.enqueue_request(r)

        return await f

    def ground_units_count(self) -> Awaitable[int]:
        f = asyncio.Future()
        r = requests.GroundUnitsCountRequest(f, self._request_timeout)
        self.enqueue_request(r)
        return f

    def ground_unit_position(
        self,
        index: int,
    ) -> Awaitable[structures.GroundUnitPosition]:
        m = msg.GroundUnitPositionRequestMessage(index)
        return self.send_message(m, self._request_timeout)

    async def all_ground_units_positions(
        self,
    ) -> Awaitable[List[structures.GroundUnitPosition]]:
        count = await self.ground_units_count()

        if not count:
            return []

        f = asyncio.Future()
        indices = range(count)
        r = requests.GroundUnitsPositionsRequest(
            future=f,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.enqueue_request(r)

        return await f

    def ships_count(self) -> Awaitable[int]:
        f = asyncio.Future()
        r = requests.ShipsCountRequest(f, self._request_timeout)
        self.enqueue_request(r)
        return f

    def ship_position(self, index: int) -> Awaitable[structures.ShipPosition]:
        m = msg.ShipPositionRequestMessage(index)
        return self.send_message(m, self._request_timeout)

    async def all_ships_positions(
        self,
    ) -> Awaitable[List[structures.ShipPosition]]:
        count = await self.ships_count()

        if not count:
            return []

        f = asyncio.Future()
        indices = range(count)
        r = requests.ShipsPositionsRequest(
            future=f,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.enqueue_request(r)

        return await f

    def stationary_objects_count(self) -> Awaitable[int]:
        f = asyncio.Future()
        r = requests.StationaryObjectsCountRequest(f, self._request_timeout)
        self.enqueue_request(r)
        return f

    def stationary_object_position(
        self,
        index: int,
    ) -> Awaitable[structures.StationaryObjectPosition]:
        m = msg.StationaryObjectPositionRequestMessage(index)
        return self.send_message(m, self._request_timeout)

    async def all_stationary_objects_positions(
        self,
    ) -> Awaitable[List[structures.StationaryObjectPosition]]:
        count = await self.stationary_objects_count()

        if not count:
            return []

        f = asyncio.Future()
        indices = range(count)
        r = requests.StationaryObjectsPositionsRequest(
            future=f,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.enqueue_request(r)

        return await f

    def houses_count(self) -> Awaitable[int]:
        f = asyncio.Future()
        r = requests.HousesCountRequest(f, self._request_timeout)
        self.enqueue_request(r)
        return f

    def house_position(
        self,
        index: int,
    ) -> Awaitable[structures.HousePosition]:
        m = msg.HousePositionRequestMessage(index)
        return self.send_message(m, self._request_timeout)

    async def all_houses_positions(
        self,
    ) -> Awaitable[List[structures.HousePosition]]:
        count = await self.houses_count()

        if not count:
            return []

        f = asyncio.Future()
        indices = range(count)
        r = requests.HousesPositionsRequest(
            future=f,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.enqueue_request(r)

        return await f
