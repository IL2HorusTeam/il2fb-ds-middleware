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
        description="Aircrafts radar for IL-2 FB DS"
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
    return parser.parse_args()


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)-8s [%(asctime)s] %(message)s")
    ch.setFormatter(formatter)
    root.addHandler(ch)


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
            if self._do_stop:
                break

            await self._do_run.wait()
            start = time.monotonic()

            try:
                await self._dl_client.refresh_radar()
                records = await self._dl_client.all_aircrafts_positions()
            except Exception as e:
                LOG.warning(f"failed to get radar data: {e}")
                records = []

            if self._do_stop:
                break

            self._print_table(records)

            if records:
                self._broadcast_records(records)

            delta = time.monotonic() - start
            delay = max(self._refresh_period - delta, 0)

            if self._do_stop:
                break

            coroutine = asyncio.sleep(delay)
            self._sleep_task = asyncio.ensure_future(coroutine)

            try:
                await self._sleep_task
            except asyncio.CancelledError:
                break
            finally:
                self._sleep_task = None

        self._stopped_ack.set_result(None)

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

    def _print_table(self, records):
        data = [
            ['Index', 'Is Human', 'ID', 'Member Index', 'X', 'Y', 'Z'],
            *map(self._format_record, records)
        ]
        table = SingleTable(table_data=data)
        LOG.info(f"\n{table.table}")

    @staticmethod
    def _format_record(record):
        return [
            record.index,
            "Y" if record.is_human else "N",
            record.id,
            record.member_index if record.member_index is not None else "N/A",
            record.pos.x,
            record.pos.y,
            record.pos.z,
        ]

    def _broadcast_records(self, records):
        data = json.dumps([r.to_primitive() for r in records])
        data = f"{data}\n".encode()

        for listener in self._listeners:
            listener.send(data)


def main():
    setup_logging()
    args = load_args()

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
