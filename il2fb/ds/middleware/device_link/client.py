# coding: utf-8

import asyncio
import logging

from typing import Tuple, Awaitable, List

from il2fb.ds.middleware.device_link import requests
from il2fb.ds.middleware.device_link import messages as msg
from il2fb.ds.middleware.device_link import structures


LOG = logging.getLogger(__name__)


Address = Tuple[str, int]


class DeviceLinkClient(asyncio.DatagramProtocol):

    def __init__(
        self,
        remote_address: Address,
        request_timeout: float=20.0,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        self._loop = loop
        self._trace = trace

        self._remote_address = remote_address
        self._request_timeout = request_timeout
        self._requests = asyncio.Queue(loop=self._loop)
        self._request = None

        self._transport = None
        self._log_message_prefix_format = self._make_log_message_prefix_format(
            remote_address=remote_address,
        )
        self._messages = []

        self._do_close = False
        self._connected_ack = asyncio.Future(loop=self._loop)
        self._closed_ack = asyncio.Future(loop=self._loop)

    @property
    def remote_address(self):
        return self._remote_address

    @staticmethod
    def _make_log_message_prefix_format(remote_address) -> str:
        addr, port = remote_address
        return f"[device link@{addr}:{port}] {{}}"

    def _prefix_log_message(self, s: str) -> str:
        return self._log_message_prefix_format.format(s)

    def connection_made(self, transport) -> None:
        LOG.debug(self._prefix_log_message(
            "transport was opened"
        ))

        self._transport = transport
        asyncio.ensure_future(self._dispatch_all_requests(), loop=self._loop)
        self._connected_ack.set_result(None)

    def wait_connected(self) -> Awaitable[None]:
        return self._connected_ack

    def wait_closed(self) -> Awaitable[None]:
        return self._closed_ack

    def connection_lost(self, e: Exception=None) -> None:
        self._closed_ack.set_result(e)

        LOG.debug(self._prefix_log_message(
            f"transport was closed (details={e or 'N/A'})"
        ))

    def close(self) -> None:
        LOG.debug(self._prefix_log_message(
            "ask dispatching of requests to stop"
        ))

        if not self._do_close:
            self._do_close = True
            self._requests.put_nowait(None)

    async def _dispatch_all_requests(self) -> None:
        LOG.info(self._prefix_log_message(
            "dispatching of requests was started"
        ))

        while True:
            try:
                await self._dispatch_request()
            except StopAsyncIteration:
                break
            except Exception:
                LOG.exception(self._prefix_log_message(
                    "failed to dispatch a single request"
                ))

        self._transport.close()

        LOG.info(self._prefix_log_message(
            "dispatching of requests was stopped"
        ))

    async def _dispatch_request(self) -> None:
        self._request = await self._requests.get()

        if not self._request or self._do_close:
            LOG.info(self._prefix_log_message(
                "got request to stop dispatching of requests"
            ))
            raise StopAsyncIteration

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"req <-- {repr(self._request)}"
            ))

        try:
            await self._request.execute(self._write_bytes)
        finally:
            self._request = None

    def _write_bytes(self, data: bytes) -> None:
        self._transport.sendto(data)

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"dat --> {repr(data)}"
            ))

    def datagram_received(self, data: bytes, addr: Address) -> None:
        if addr != self._remote_address:
            if self._trace:
                LOG.warning(self._prefix_log_message(
                    f"dat <-? unknown sender {addr}, skip"
                ))
            return

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"dat <-- {repr(data)}"
            ))

        if not self._request:
            if self._trace:
                LOG.warning(self._prefix_log_message(
                    f"req N/A, skip"
                ))
            return

        try:
            self._request.data_received(data)
        except Exception:
            LOG.exception(self._prefix_log_message(
                "failed to handle response"
            ))

    def error_received(self, e) -> None:
        if self._trace:
            LOG.error(self._prefix_log_message(
                f"err <-- {e}"
            ))

        if self._request:
            self._request.set_exception(e)

    def schedule_request(self, request: requests.DeviceLinkRequest) -> None:
        if self._do_close:
            raise ConnectionAbortedError(
                "client is closed and does not accept requests"
            )

        self._requests.put_nowait(request)

    def send_messages(
        self,
        messages: List[msg.DeviceLinkRequestMessage],
    ) -> Awaitable[List[msg.DeviceLinkMessage]]:
        r = requests.DeviceLinkRequest(
            messages=messages,
            loop=self._loop,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    def refresh_radar(self) -> Awaitable[None]:
        r = requests.RefreshRadarRequest(
            loop=self._loop,
        )
        self.schedule_request(r)
        return r.wait()

    def moving_aircrafts_count(self) -> Awaitable[int]:
        r = requests.MovingAircraftsCountRequest(
            loop=self._loop,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    def moving_aircraft_position(
        self,
        index: int,
    ) -> Awaitable[structures.MovingAircraftPosition]:
        r = requests.MovingAircraftsPositionsRequest(
            loop=self._loop,
            indices=[index, ],
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    async def all_moving_aircrafts_positions(
        self,
    ) -> Awaitable[List[structures.MovingAircraftPosition]]:
        count = await self.moving_aircrafts_count()

        if not count:
            return []

        indices = range(count)
        r = requests.MovingAircraftsPositionsRequest(
            loop=self._loop,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)

        return (await r.wait())

    def moving_ground_units_count(self) -> Awaitable[int]:
        r = requests.MovingGroundUnitsCountRequest(
            loop=self._loop,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    def moving_ground_unit_position(
        self,
        index: int,
    ) -> Awaitable[structures.MovingGroundUnitPosition]:
        r = requests.MovingGroundUnitsPositionsRequest(
            loop=self._loop,
            indices=[index, ],
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    async def all_moving_ground_units_positions(
        self,
    ) -> Awaitable[List[structures.MovingGroundUnitPosition]]:
        count = await self.moving_ground_units_count()

        if not count:
            return []

        indices = range(count)
        r = requests.MovingGroundUnitsPositionsRequest(
            loop=self._loop,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)

        return (await r.wait())

    def ships_count(self) -> Awaitable[int]:
        r = requests.ShipsCountRequest(
            loop=self._loop,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    def ship_position(self, index: int) -> Awaitable[structures.ShipPosition]:
        r = requests.ShipsPositionsRequest(
            loop=self._loop,
            indices=[index, ],
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    async def all_ships_positions(
        self,
    ) -> Awaitable[List[structures.ShipPosition]]:
        count = await self.ships_count()

        if not count:
            return []

        indices = range(count)
        r = requests.ShipsPositionsRequest(
            loop=self._loop,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)

        return (await r.wait())

    def stationary_objects_count(self) -> Awaitable[int]:
        r = requests.StationaryObjectsCountRequest(
            loop=self._loop,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    def stationary_object_position(
        self,
        index: int,
    ) -> Awaitable[structures.StationaryObjectPosition]:
        r = requests.StationaryObjectsPositionsRequest(
            loop=self._loop,
            indices=[index, ],
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    async def all_stationary_objects_positions(
        self,
    ) -> Awaitable[List[structures.StationaryObjectPosition]]:
        count = await self.stationary_objects_count()

        if not count:
            return []

        indices = range(count)
        r = requests.StationaryObjectsPositionsRequest(
            loop=self._loop,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)

        return (await r.wait())

    def houses_count(self) -> Awaitable[int]:
        r = requests.HousesCountRequest(
            loop=self._loop,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    def house_position(
        self,
        index: int,
    ) -> Awaitable[structures.HousePosition]:
        r = requests.HousesPositionsRequest(
            loop=self._loop,
            indices=[index, ],
            timeout=self._request_timeout,
        )
        self.schedule_request(r)
        return r.wait()

    async def all_houses_positions(
        self,
    ) -> Awaitable[List[structures.HousePosition]]:
        count = await self.houses_count()

        if not count:
            return []

        indices = range(count)
        r = requests.HousesPositionsRequest(
            loop=self._loop,
            indices=indices,
            timeout=self._request_timeout,
        )
        self.schedule_request(r)

        return (await r.wait())
