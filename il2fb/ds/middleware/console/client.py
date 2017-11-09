# coding: utf-8

import asyncio
import concurrent
import functools
import logging

from collections import OrderedDict
from typing import List, Awaitable, Callable

from il2fb.commons.organization import Belligerent

from il2fb.ds.middleware.console import events, requests, structures
from il2fb.ds.middleware.console.constants import (
    MESSAGE_DELIMITER, LINE_DELIMITER, LINE_DELIMITER_LENGTH,
    CHAT_MESSAGE_MAX_LENGTH,
)
from il2fb.ds.middleware.console.helpers import (
    is_command_prompt, is_command_prompt_continuation, is_user_input,
    is_server_input,
)


LOG = logging.getLogger(__name__)


class ConsoleClient(asyncio.Protocol):

    def __init__(
        self,
        request_timeout: float=20.0,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        self._loop = loop
        self._trace = trace

        self._request_timeout = request_timeout
        self._requests = asyncio.Queue(loop=self._loop)
        self._request = None

        self._transport = None
        self._remote_address = None
        self._log_message_prefix_format = None

        self._messages = []
        self._messages_buffer = []

        self._do_close = False
        self._connected_ack = asyncio.Future(loop=self._loop)
        self._closed_ack = asyncio.Future(loop=self._loop)

        self._data_subscribers = []
        self._chat_subscribers = []
        self._human_connection_subscribers = []

        self._events_to_handlers_map = OrderedDict([
            (
                events.ChatMessageWasReceived,
                self._handle_chat_event,
            ),
            (
                events.HumanHasStartedConnection,
                self._handle_human_connection_event,
            ),
            (
                events.HumanHasConnected,
                self._handle_human_connection_event,
            ),
            (
                events.HumanHasDisconnected,
                self._handle_human_connection_event,
            ),
        ])

    def subscribe_to_data(
        self,
        subscriber: Callable[[bytes], bool],
    ) -> None:
        """
        Not thread-safe.

        """
        self._data_subscribers.append(subscriber)

    def unsubscribe_from_data(
        self,
        subscriber: Callable[[bytes], bool],
    ) -> None:
        """
        Not thread-safe.

        """
        self._data_subscribers.remove(subscriber)

    def subscribe_to_chat(
        self,
        subscriber: Callable[[events.ChatMessageWasReceived], None],
    ) -> None:
        """
        Not thread-safe.

        """
        self._chat_subscribers.append(subscriber)

    def unsubscribe_from_chat(
        self,
        subscriber: Callable[[events.ChatMessageWasReceived], None],
    ) -> None:
        """
        Not thread-safe.

        """
        self._chat_subscribers.remove(subscriber)

    def _handle_chat_event(self, event: events.ChatMessageWasReceived) -> None:
        """
        Not thread-safe.

        """
        for subscriber in self._chat_subscribers:
            try:
                subscriber(event)
            except Exception:
                LOG.exception(self._prefix_log_message(
                    f"failed to send chat event {event} to "
                    f"subscriber {subscriber}"
                ))

    def subscribe_to_human_connection_events(
        self,
        subscriber: Callable[[events.HumanConnectionEvent], None],
    ) -> None:
        """
        Not thread-safe.

        """
        self._human_connection_subscribers.append(subscriber)

    def unsubscribe_from_human_connection_events(
        self,
        subscriber: Callable[[events.HumanConnectionEvent], None],
    ) -> None:
        """
        Not thread-safe.

        """
        self._human_connection_subscribers.remove(subscriber)

    def _handle_human_connection_event(
        self,
        event: events.HumanConnectionEvent,
    ) -> None:
        """
        Not thread-safe.

        """
        for subscriber in self._human_connection_subscribers:
            try:
                subscriber(event)
            except Exception:
                LOG.exception(self._prefix_log_message(
                    f"failed to send human connection event {event} to "
                    f"subscriber {subscriber}"
                ))

    def connection_made(self, transport) -> None:
        self._transport = transport
        self._remote_address = transport.get_extra_info('peername')
        self._log_message_prefix_format = self._make_log_message_prefix_format(
            remote_address=self._remote_address,
        )

        LOG.debug(self._prefix_log_message(
            "connection was established"
        ))

        asyncio.ensure_future(self._dispatch_all_requests(), loop=self._loop)
        self._connected_ack.set_result(None)

    @staticmethod
    def _make_log_message_prefix_format(remote_address) -> str:
        addr, port = remote_address
        return f"[console@{addr}:{port}] {{}}"

    def _prefix_log_message(self, s: str) -> str:
        return self._log_message_prefix_format.format(s)

    def wait_connected(self) -> Awaitable[None]:
        return self._connected_ack

    def connection_lost(self, e: Exception) -> None:
        if not self._do_close:
            enlog = LOG.error
            self.close()
        else:
            enlog = LOG.info

        enlog(self._prefix_log_message(
            f"connection was lost (details={e or 'N/A'})"
        ))

    def close(self) -> None:
        LOG.debug(self._prefix_log_message(
            "ask dispatching of requests to stop"
        ))

        if not self._do_close:
            self._do_close = True
            self._requests.put_nowait(None)

    def wait_closed(self) -> Awaitable[None]:
        return self._closed_ack

    def write_bytes(self, data: bytes) -> None:
        self._transport.write(data)

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"dat --> {repr(data)}"
            ))

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

        if not self._closed_ack.done():
            self._closed_ack.set_result(None)

        LOG.info(self._prefix_log_message(
            "dispatching of requests was stopped"
        ))

    async def _dispatch_request(self) -> None:
        if self._do_close:
            self._stop()

        self._request = await self._requests.get()

        if not self._request or self._do_close:
            self._stop()

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"req <-- {repr(self._request)}"
            ))

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
        LOG.info(self._prefix_log_message(
            "got request to stop dispatching of requests"
        ))
        raise StopAsyncIteration

    @staticmethod
    def _on_wrapped_future_done(
        timeout_future: asyncio.Future,
        wrapped_future: asyncio.Future,
    ) -> None:
        if not timeout_future.done():
            timeout_future.set_result(None)

    def data_received(self, data: bytes) -> None:
        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"dat <-- {repr(data)}"
            ))

        for subscriber in self._data_subscribers:
            try:
                is_trapped = subscriber(data)
            except Exception:
                LOG.exception(self._prefix_log_message(
                    f"failed to send data to subscriber {subscriber}"
                ))
            else:
                if is_trapped:
                    return

        message = data.decode().strip(MESSAGE_DELIMITER)

        if (LINE_DELIMITER not in message) and not is_command_prompt(message):
            self._on_message_chunk(message)
            return

        messages = message.split(MESSAGE_DELIMITER)
        messages = self._concat_messages_with_buffer(messages)

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"msg <<< {messages}"
            ))

        for message in messages:
            if is_command_prompt(message):
                self._on_command_prompt()

            elif is_command_prompt_continuation(message):
                if self._trace:
                    LOG.debug(self._prefix_log_message(
                        "cmd continuation, skip"
                    ))

            elif message.endswith(LINE_DELIMITER):
                message = message[:-LINE_DELIMITER_LENGTH]
                self._on_message(message)

            else:
                self._messages_buffer.append(message)
                if self._trace:
                    LOG.debug(self._prefix_log_message(
                        f"buf <-- {repr(message)}"
                    ))

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"msg === {self._messages}"
            ))

    def _on_message_chunk(self, chunk: str) -> None:
        self._messages_buffer.append(chunk)

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"buf <-- {repr(chunk)}"
            ))

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

            if self._trace:
                LOG.debug(self._prefix_log_message(
                    f"buf >>> {repr(message)}"
                ))

        return messages

    def _on_command_prompt(self) -> None:
        if self._trace:
            LOG.debug(self._prefix_log_message(
                "cmd <<<"
            ))

        if self._request is None:
            if self._trace:
                LOG.warning(self._prefix_log_message(
                    "req N/A, skip"
                ))
        else:
            self._finalize_request()

    def _finalize_request(self) -> None:
        messages, self._messages = self._messages, []

        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"res {messages}"
            ))

        if any(
            is_user_input(m) for m in messages
        ):
            if self._trace:
                LOG.debug(self._prefix_log_message(
                    "usr, skip"
                ))
            return

        if any(
            is_server_input(m) for m in messages
        ):
            if self._trace:
                LOG.debug(self._prefix_log_message(
                    "srv, skip"
                ))
            return

        try:
            self._request.set_result(messages)
        except Exception as e:
            LOG.exception(self._prefix_log_message(
                "failed to set result of request"
            ))
            try:
                self._request.set_exception(e)
            except Exception:
                LOG.exception(self._prefix_log_message(
                    "failed to set exception of request"
                ))

    def _on_message(self, message: str) -> None:
        if self._trace:
            LOG.debug(self._prefix_log_message(
                f"msg <-- {repr(message)}"
            ))

        if not message:
            if self._trace:
                LOG.debug(self._prefix_log_message(
                    "empty, skip"
                ))

        elif self._try_to_extract_and_handle_event_from_string(message):
            return

        elif self._request is None:
            if self._trace:
                LOG.warning(self._prefix_log_message(
                    "req N/A, skip"
                ))

        else:
            self._messages.append(message)

    def _try_to_extract_and_handle_event_from_string(self, s: str) -> bool:
        for event_class, handler in self._events_to_handlers_map.items():
            try:
                event = event_class.from_s(s)
            except Exception:
                LOG.exception(self._prefix_log_message(
                    f"failed to create event {event_class} from string "
                    f"{repr(s)}"
                ))
                continue

            if not event:
                continue

            try:
                handler(event)
            except Exception:
                LOG.exception(self._prefix_log_message(
                    f"failed to handle event {event}"
                ))
            finally:
                return True

        return False

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
