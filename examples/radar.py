#! /usr/bin/env python
# coding: utf-8

import argparse
import asyncio
import json
import logging
import sys
import time

from terminaltables import SingleTable

from il2fb.ds.middleware.device_link.client import DeviceLinkClient


LOG = logging.getLogger(__name__)


def load_args():
    parser = argparse.ArgumentParser(
        description="Radar for IL-2 FB DS"
    )
    parser.add_argument(
        '--dl-addr',
        dest='dl_address',
        type=str,
        default="127.0.0.1",
        help="IP address of Device Link. Default: 127.0.0.1",
    )
    parser.add_argument(
        '--dl-port',
        dest='dl_port',
        type=int,
        default=10000,
        help="IP port of Device Link. Default: 10000",
    )
    parser.add_argument(
        '--bind-addr',
        dest='bind_address',
        type=str,
        default="127.0.0.1",
        help=(
            "IP address for radar listeners to connect to. Default: 127.0.0.1"
        ),
    )
    parser.add_argument(
        '--bind-port',
        dest='bind_port',
        type=int,
        default=10080,
        help="IP port for radar listeners to connect to. Default: 10080",
    )
    parser.add_argument(
        '-r', '--refresh',
        dest='radar_refresh_period',
        type=float,
        default=5.0,
        help="Refresh period of radar in seconds. Default: 5.0",
    )
    parser.add_argument(
        '-t', '--timeout',
        dest='request_timeout',
        type=float,
        default=20.0,
        help="Request execution timeout in seconds. Default: 20.0",
    )
    parser.add_argument(
        '-d', '--debug',
        dest='debug',
        action='store_true',
        help="Enable debug mode",
    )
    return parser.parse_args()


def setup_logging(level):
    root = logging.getLogger()
    root.setLevel(level)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    formatter = logging.Formatter("[%(levelname)-8s %(asctime)s] %(message)s")
    ch.setFormatter(formatter)
    root.addHandler(ch)


def _format_all_aircrafts(records):
    data = [
        ['Index', 'Is Human', 'ID', 'Member Index', 'X', 'Y', 'Z'],
        *map(_format_single_aircraft, records)
    ]
    table = SingleTable(table_data=data, title='Air')
    return table.table


def _format_single_aircraft(record):
    return [
        record.index,
        "Y" if record.is_human else "N",
        record.id,
        record.member_index if record.member_index is not None else "N/A",
        record.pos.x,
        record.pos.y,
        record.pos.z,
    ]


def _format_all_moving_ground_units(records):
    data = [
        ['Index', 'ID', 'Member Index', 'X', 'Y', 'Z'],
        *map(_format_single_moving_ground_unit, records)
    ]
    table = SingleTable(table_data=data, title='Ground')
    return table.table


def _format_single_moving_ground_unit(record):
    return [
        record.index,
        record.id,
        record.member_index if record.member_index is not None else "N/A",
        record.pos.x,
        record.pos.y,
        record.pos.z,
    ]


def _format_all_ships(records):
    data = [
        ['Index', 'ID', 'X', 'Y', ],
        *map(_format_single_ship, records)
    ]
    table = SingleTable(table_data=data, title='Ship')
    return table.table


def _format_single_ship(record):
    return [
        record.index,
        record.id,
        record.pos.x,
        record.pos.y,
    ]


class ServerClientProtocol(asyncio.Protocol):

    def __init__(self, manager):
        self._manager = manager
        self._transport = None

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        LOG.info(f"connection with {peername} was established")
        self._transport = transport
        self._manager.register(self)

    def connection_lost(self, exc):
        peername = self._transport.get_extra_info('peername')
        LOG.info(f"connection with {peername} was lost")
        self._manager.unregister(self)

    def close(self):
        self._transport.close()

    def send(self, data):
        self._transport.write(data)


class Radar:

    def __init__(self, dl_client, refresh_period):
        self._dl_client = dl_client
        self._listeners = []
        self._refresh_period = refresh_period

        self._do_run = asyncio.Event()
        self._do_run.clear()

        self._do_stop = False
        self._stopped_ack = asyncio.Future()
        self._sleep_task = None

    async def run(self):
        while True:
            try:
                await self._check_state()

                start = time.monotonic()

                try:
                    await self._tick()
                except Exception:
                    LOG.exception("unhandled error")

                await self._check_state()

                delta = time.monotonic() - start
                delay = max(self._refresh_period - delta, 0)

                if not delay:
                    return

                coroutine = asyncio.sleep(delay)
                self._sleep_task = asyncio.ensure_future(coroutine)

                try:
                    await self._sleep_task
                except asyncio.CancelledError:
                    raise StopAsyncIteration
                finally:
                    self._sleep_task = None
            except StopAsyncIteration:
                break

        self._stopped_ack.set_result(None)

    async def _tick(self):
        await self._dl_client.refresh_radar()

        try:
            aircrafts = await self._dl_client.all_aircrafts_positions()
        except Exception as e:
            LOG.warning(
                f"failed to get coordinates of aircrafts: "
                f"{str(e) or e.__class__.__name__}"
            )
            aircrafts = []

        try:
            moving_ground_units = (
                await self._dl_client.all_moving_ground_units_positions()
            )
        except Exception as e:
            LOG.warning(
                f"failed to get coordinates of moving ground units: "
                f"{str(e) or e.__class__.__name__}"
            )
            moving_ground_units = []

        try:
            ships = await self._dl_client.all_ships_positions()
        except Exception as e:
            LOG.warning(
                f"failed to get coordinates of ships: "
                f"{str(e) or e.__class__.__name__}"
            )
            ships = []
        else:
            ships = [x for x in ships if not x.is_stationary]

        data = {
            'aircrafts': aircrafts,
            'moving_ground_units': moving_ground_units,
            'ships': ships,
        }

        self._print_data(data)
        self._broadcast_data(data)

    async def _check_state(self):
        if self._do_stop:
            raise StopAsyncIteration

        await self._do_run.wait()

    def stop(self):
        self._do_stop = True

        if self._sleep_task:
            self._sleep_task.cancel()

        if not self._do_run.is_set():
            self._do_run.set()

    def wait_stopped(self):
        return self._stopped_ack

    def register(self, listener):
        self._listeners.append(listener)

        if not self._do_run.is_set():
            self._do_run.set()

    def unregister(self, listener):
        self._listeners.remove(listener)

        if not self._listeners:
            self._do_run.clear()

    @classmethod
    def _print_data(cls, data):
        s = "\n".join([
            "coordinates:",
            _format_all_aircrafts(data['aircrafts']),
            _format_all_moving_ground_units(data['moving_ground_units']),
            _format_all_ships(data['ships']),
        ])
        LOG.info(s)

    def _broadcast_data(self, data):
        payload = json.dumps({
            key: [v.to_primitive() for v in values]
            for key, values in data.items()
        })
        payload = f"{payload}\n".encode()

        for listener in self._listeners:
            listener.send(payload)


def main():
    args = load_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)

    loop = asyncio.get_event_loop()

    remote_address = (args.dl_address, args.dl_port)
    dl_client = DeviceLinkClient(remote_address, args.request_timeout)
    dl_awaitable = loop.create_datagram_endpoint(
        lambda: dl_client,
        remote_addr=remote_address,
    )

    radar = Radar(dl_client, args.radar_refresh_period)
    asyncio.async(radar.run())

    server_awaitable = loop.create_server(
        lambda: ServerClientProtocol(manager=radar),
        args.bind_address,
        args.bind_port,
    )
    server = loop.run_until_complete(server_awaitable)
    loop.run_until_complete(dl_awaitable)

    local_addr = server.sockets[0].getsockname()
    LOG.info(f"listening for incoming connections at {local_addr}")

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        LOG.info("got request to stop radar")
    finally:
        server.close()
        dl_client.close()
        radar.stop()
        loop.run_until_complete(server.wait_closed())
        loop.run_until_complete(radar.wait_stopped())
        loop.close()
        LOG.info("radar is stopped")


if __name__ == '__main__':
    main()
