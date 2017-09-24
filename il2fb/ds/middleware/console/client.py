# coding: utf-8

import asyncio
import concurrent
import functools
import logging

from typing import List, Awaitable, Callable

from il2fb.commons.organization import Belligerent

from . import requests, parsers, structures
from .constants import (
    MESSAGE_DELIMITER, LINE_DELIMITER, LINE_DELIMITER_LENGTH,
    CHAT_MESSAGE_MAX_LENGTH,
)
from .helpers import (
    is_user_input, is_server_input, is_chat_message, is_command_prompt,
    is_command_prompt_continuation,
)


LOG = logging.getLogger(__name__)


class ConsoleClient(asyncio.Protocol):

    def __init__(
        self,
        request_timeout: float=20.0,
        loop: asyncio.AbstractEventLoop=None,
    ):
        self._loop = loop

        self._request_timeout = request_timeout
        self._requests = asyncio.Queue(loop=self._loop)
        self._request = None

        self._transport = None
        self._messages = []
        self._messages_buffer = []

        self._do_close = False
        self._connected_ack = asyncio.Future(loop=self._loop)
        self._closed_ack = asyncio.Future(loop=self._loop)

        self._data_listeners = []

    def register_data_listener(
        self,
        listener: Callable[[bytes], bool],
    ) -> None:
        self._data_listeners.append(listener)

    def unregister_data_listener(
        self,
        listener: Callable[[bytes], bool],
    ) -> None:
        self._data_listeners.remove(listener)

    def connection_made(self, transport) -> None:
        self._transport = transport
        asyncio.async(self._dispatch_all_requests(), loop=self._loop)
        self._connected_ack.set_result(None)

    def wait_connected(self) -> Awaitable[None]:
        return self._connected_ack

    def connection_lost(self, e: Exception) -> None:
        if not self._do_close:
            enlog = LOG.error
            self.close()
        else:
            enlog = LOG.info

        enlog(f"console connection was lost, details: {e or 'N/A'}")

    def close(self) -> None:
        LOG.debug("ask dispatching of console requests to stop")
        if not self._do_close:
            self._do_close = True
            self._requests.put_nowait(None)

    def wait_closed(self) -> Awaitable[None]:
        return self._closed_ack

    def write_bytes(self, data: bytes) -> None:
        self._transport.write(data)
        LOG.debug(f"dat --> {repr(data)}")

    async def _dispatch_all_requests(self) -> None:
        LOG.info("dispatching of console requests has started")

        while True:
            try:
                await self._dispatch_request()
            except StopAsyncIteration:
                break
            except Exception:
                LOG.exception("failed to dispatch a single console request")

        LOG.info("dispatching of console requests has stopped")

        self._transport.close()

        if not self._closed_ack.done():
            self._closed_ack.set_result(None)

    async def _dispatch_request(self) -> None:
        if self._do_close:
            self._stop()

        self._request = await self._requests.get()

        if not self._request or self._do_close:
            self._stop()

        LOG.debug(f"req <-- {repr(self._request)}")

        data = f"{str(self._request)}{MESSAGE_DELIMITER}".encode()

        timeout_future = asyncio.Future(loop=self._loop)
        self._request.add_done_callback(functools.partial(
            self._on_wrapped_future_done, timeout_future,
        ))
        self.write_bytes(data)

        try:
            await asyncio.wait_for(
                timeout_future,
                self._request_timeout,
                loop=self._loop,
            )
        except concurrent.futures.TimeoutError as e:
            self._request.set_exception(e)
        finally:
            self._request = None

    def _stop(self) -> None:
        LOG.info("got request to stop dispatching console requests")
        raise StopAsyncIteration

    @staticmethod
    def _on_wrapped_future_done(
        timeout_future: asyncio.Future,
        wrapped_future: asyncio.Future,
    ) -> None:
        if not timeout_future.done():
            timeout_future.set_result(None)

    def data_received(self, data: bytes) -> None:
        LOG.debug(f"dat <-- {repr(data)}")

        for listener in self._data_listeners:
            try:
                is_trapped = listener(data)
            except Exception:
                LOG.exception(f"failed to feed data to listener {listener}")
            else:
                if is_trapped:
                    return

        message = data.decode().strip(MESSAGE_DELIMITER)

        if (LINE_DELIMITER not in message) and not is_command_prompt(message):
            self._on_message_chunk(message)
            return

        messages = message.split(MESSAGE_DELIMITER)
        messages = self._concat_messages_with_buffer(messages)
        LOG.debug(f"msg <<< {messages}")

        for message in messages:
            if is_command_prompt(message):
                self._on_command_prompt()
            elif is_command_prompt_continuation(message):
                LOG.debug("cmd continuation, skip")
            elif message.endswith(LINE_DELIMITER):
                message = message[:-LINE_DELIMITER_LENGTH]
                self._on_message(message)
            else:
                self._messages_buffer.append(message)
                LOG.debug(f"buf <-- {repr(message)}")

        LOG.debug(f"msg === {self._messages}")

    def _on_message_chunk(self, chunk: str) -> None:
        self._messages_buffer.append(chunk)
        LOG.debug(f"buf <-- {repr(chunk)}")

    def _concat_messages_with_buffer(
        self,
        messages: List[str],
    ) -> List[str]:
        if self._messages_buffer:
            chunk = messages[0]
            self._messages_buffer.append(chunk)

            message = ''.join(self._messages_buffer)
            messages[0] = message

            self._messages_buffer = []
            LOG.debug(f"buf >>> {repr(message)}")

        return messages

    def _on_command_prompt(self) -> None:
        LOG.debug("cmd <<<")

        if self._request is None:
            LOG.warning("req N/A, skip")
        else:
            self._finalize_request()

    def _finalize_request(self) -> None:
        messages, self._messages = self._messages, []
        LOG.debug(f"res {messages}")

        if any(
            is_user_input(m) for m in messages
        ):
            LOG.debug("usr, skip")
            return

        if any(
            is_server_input(m) for m in messages
        ):
            LOG.debug("srv, skip")
            return

        try:
            self._request.set_result(messages)
        except Exception as e:
            LOG.exception("failed to set result of request")
            try:
                self._request.set_exception(e)
            except Exception:
                LOG.exception("failed to set exception of request")

    def _on_message(self, message: str) -> None:
        LOG.debug("msg <-- {!r}".format(message))

        if not message:
            LOG.debug("empty, skip")
        elif is_chat_message(message):
            self._on_chat_message(message)
        elif self._try_parse_message(message):
            return
        elif self._request is None:
            LOG.warning("req N/A, skip")
        else:
            self._messages.append(message)

    def _on_chat_message(self, message: str) -> None:
        try:
            data = parsers.parse_chat_message(message)
            message = structures.ChatMessage(**data)
        except Exception:
            LOG.exception("failed to parse chat message")
            return

        try:
            self.on_chat_message(message)
        except Exception:
            LOG.exception("failed to process chat message")

    def _try_parse_message(self, message):
        for parser, structure, handler in (
            (
                parsers.parse_user_is_joining,
                structures.UserIsJoining,
                self.on_user_is_joining,
            ),
            (
                parsers.parse_user_has_joined,
                structures.UserHasJoined,
                self.on_user_has_joined,
            ),
            (
                parsers.parse_user_has_left,
                structures.UserHasLeft,
                self.on_user_has_left,
            ),
        ):
            try:
                data = parser(message)
            except Exception:
                LOG.exception(
                    f"failed to parse message "
                    f"(message={repr(message)}, parser={repr(parser)})"
                )
                continue

            if not data:
                continue

            try:
                message = structure(**data)
                handler(message)
            except Exception:
                LOG.exception(
                    f"failed to process message "
                    f"(message={repr(message)}, parser={repr(parser)})"
                )
            finally:
                return True

        return False

    def on_chat_message(self, message: structures.ChatMessage) -> None:
        LOG.info(f"chat({message.to_primitive()})")

    def on_user_is_joining(self, message: structures.UserIsJoining) -> None:
        LOG.info(f"joining({message.to_primitive()})")

    def on_user_has_joined(self, message: structures.UserHasJoined) -> None:
        LOG.info(f"joined({message.to_primitive()})")

    def on_user_has_left(self, message: structures.UserHasLeft) -> None:
        LOG.info(f"left({message.to_primitive()})")

    def enqueue_request(self, request: requests.ConsoleRequest) -> None:
        if self._do_close:
            raise ConnectionAbortedError(
                "client is closed and does not accept requests"
            )

        self._requests.put_nowait(request)

    def server_info(self) -> Awaitable[structures.ServerInfo]:
        f = asyncio.Future(loop=self._loop)
        r = requests.ServerInfoRequest(f)
        self.enqueue_request(r)
        return f

    def user_list(self) -> Awaitable[List[structures.User]]:
        f = asyncio.Future(loop=self._loop)
        r = requests.UserListRequest(f)
        self.enqueue_request(r)
        return f

    def user_stats(self) -> Awaitable[List[structures.UserStatistics]]:
        f = asyncio.Future(loop=self._loop)
        r = requests.UserStatisticsRequest(f)
        self.enqueue_request(r)
        return f

    async def user_count(self) -> Awaitable[int]:
        users = await self.user_list()
        return len(users)

    def kick_by_callsign(self, callsign: str) -> Awaitable[None]:
        f = asyncio.Future(loop=self._loop)
        r = requests.KickByCallsignRequest(f, callsign)
        self.enqueue_request(r)
        return f

    def kick_by_number(self, number: int) -> Awaitable[None]:
        f = asyncio.Future(loop=self._loop)
        r = requests.KickByNumberRequest(f, number)
        self.enqueue_request(r)
        return f

    def kick_first(self) -> Awaitable[None]:
        return self.kick_by_number(1)

    async def kick_all(self) -> Awaitable[int]:
        count = await self.user_count()

        for i in range(count):
            await self.kick_first()

        return count

    def chat_all(self, message: str) -> Awaitable[None]:
        return self._chat(message, "ALL")

    def chat_user(self, message: str, callsign: str) -> Awaitable[None]:
        return self._chat(message, f"TO {callsign}")

    def chat_belligerent(
        self,
        message: str,
        belligerent: Belligerent,
    ) -> Awaitable[None]:
        return self._chat(message, f"ARMY {belligerent.value}")

    async def _chat(self, message: str, target: str) -> Awaitable[None]:
        last = 0
        total = len(message)

        while last < total:
            step = min(CHAT_MESSAGE_MAX_LENGTH, total - last)
            chunk = message[last:last + step]
            chunk = chunk.encode('unicode-escape').decode()

            f = asyncio.Future(loop=self._loop)
            r = requests.ChatRequest(f, chunk, target)
            self.enqueue_request(r)
            await f

            last += step

    def mission_status(self) -> Awaitable[structures.MissionInfo]:
        f = asyncio.Future(loop=self._loop)
        r = requests.MissionStatusRequest(f)
        self.enqueue_request(r)
        return f

    def mission_load(self, file_path) -> Awaitable[None]:
        f = asyncio.Future(loop=self._loop)
        r = requests.MissionLoadRequest(f, file_path)
        self.enqueue_request(r)
        return f

    def mission_begin(self) -> Awaitable[None]:
        f = asyncio.Future(loop=self._loop)
        r = requests.MissionBeginRequest(f)
        self.enqueue_request(r)
        return f

    def mission_end(self) -> Awaitable[None]:
        f = asyncio.Future(loop=self._loop)
        r = requests.MissionEndRequest(f)
        self.enqueue_request(r)
        return f

    def mission_destroy(self) -> Awaitable[None]:
        f = asyncio.Future(loop=self._loop)
        r = requests.MissionDestroyRequest(f)
        self.enqueue_request(r)
        return f
