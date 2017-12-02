# coding: utf-8

import asyncio
import itertools
import logging
import re
import time

from itertools import takewhile
from typing import Any, Awaitable, List, Callable, Optional

from il2fb.commons import MissionStatuses
from il2fb.commons.organization import Belligerents

from il2fb.ds.middleware.console import structures
from il2fb.ds.middleware.console.constants import MESSAGE_DELIMITER
from il2fb.ds.middleware.console.exceptions import ConsoleRequestError


LOG = logging.getLogger(__name__)


class ConsoleRequest:

    def __init__(
        self,
        body: str,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        self.body = body

        self._timeout = timeout
        self._trace = trace
        self._loop = loop

        self._response_messages = []
        self._future = asyncio.Future(loop=loop)

    def result(self) -> Awaitable[Any]:
        return self._future

    async def execute(
        self,
        writer: Callable[[bytes], None],
    ) -> Awaitable[None]:
        start_time = time.monotonic()

        LOG.debug("console request execution start")

        try:
            await self._execute(writer)
        except Exception as e:
            if self._future.done():
                LOG.exception("failed to execute console request")
            else:
                self._future.set_exception(e)
        finally:
            execution_time = time.monotonic() - start_time
            LOG.debug(
                "console request execution time: {:.6f} s"
                .format(execution_time)
            )

    async def _execute(
        self,
        writer: Callable[[bytes], None],
    ) -> Awaitable[None]:

        data = f"{self.body}{MESSAGE_DELIMITER}".encode()
        writer(data)

        future = self._future

        if self._timeout:
            future = asyncio.wait_for(future, self._timeout, loop=self._loop)

        await future

    def message_received(self, message: Optional[str]) -> None:
        messages = self._response_messages

        if message is not None:
            messages.append(message)
            if self._trace:
                LOG.debug(f"msg === {messages}")

            return

        if self._trace:
            LOG.debug(f"res {messages}")

        if self._future.done():
            LOG.debug("console request was aborted")
            return

        try:
            result = self._extract_result(messages)
        except Exception as e:
            self._future.set_exception(e)
        else:
            self._future.set_result(result)

    def _extract_result(self, messages: List[str]) -> Optional[Any]:
        pass

    def __str__(self) -> str:
        return self.body

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self.body}')>"


class GetServerInfoRequest(ConsoleRequest):

    def __init__(
        self,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body="server",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )

    def _extract_result(self, messages: List[str]) -> structures.ServerInfo:
        messages = self._maybe_filter_messages(messages)
        messages = [
            m.split(':', 1)[1].strip()
            for m in messages
        ]
        return structures.ServerInfo(
            type=messages[0],
            name=messages[1],
            description=messages[2],
        )

    @staticmethod
    def _maybe_filter_messages(messages: List[str]) -> List[str]:
        if not messages[0].startswith("Type:"):
            messages = messages[::-1]
            messages = list(takewhile(
                lambda s: not s.startswith("Type:"),
                messages,
            ))
            messages = messages[::-1]

        return messages


class GetHumansListRequest(ConsoleRequest):

    def __init__(
        self,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body="user",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )

    def _extract_result(self, messages: List[str]) -> List[structures.Human]:
        messages = self._maybe_filter_messages(messages)

        # Skip header
        messages = messages[1:]
        return [
            self._human_from_message(message)
            for message in messages
        ]

    @staticmethod
    def _maybe_filter_messages(messages: List[str]) -> List[str]:
        if not messages[0].startswith(" N"):
            messages = messages[::-1]
            messages = list(takewhile(
                lambda s: not s.startswith(" N"),
                messages,
            ))
            messages = messages[::-1]

        return messages

    @staticmethod
    def _human_from_message(message: str) -> structures.Human:
        message = message.strip()
        data = re.split('\s{2,}', message)[1:]

        callsign = data.pop(0)
        ping = int(data.pop(0))
        score = int(data.pop(0))

        belligerent = data.pop(0)
        belligerent = int(re.search('\d+', belligerent).group())
        belligerent = Belligerents.get_by_value(belligerent)

        if data:
            designation = data.pop(0)
            type = data.pop(0)
            aircraft = structures.Aircraft(
                designation=designation,
                type=type,
            )
        else:
            aircraft = None

        return structures.Human(
            callsign=callsign,
            ping=ping,
            score=score,
            belligerent=belligerent,
            aircraft=aircraft,
        )


class GetHumansStatisticsRequest(ConsoleRequest):

    def __init__(
        self,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body="user STAT",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )

    def _extract_result(
        self,
        messages: List[str],
    ) -> List[structures.HumanStatistics]:

        messages = self._maybe_filter_messages(messages)

        results = []
        buffer = {}
        field_names = itertools.cycle(structures.HumanStatistics.__slots__)

        for message in messages[1:]:

            if message.startswith('-'):
                item = structures.HumanStatistics(**buffer)
                results.append(item)
                continue

            field_name = next(field_names)
            value = message.replace('\\t', '').split(': ')[1]

            if field_name not in {'callsign', 'state'}:
                value = int(value)

            buffer[field_name] = value

        return results

    @staticmethod
    def _maybe_filter_messages(messages: List[str]) -> List[str]:
        if not messages[0].startswith("-----"):
            messages = messages[::-1]
            messages = list(takewhile(
                lambda s: not s.startswith("-----"),
                messages,
            ))
            messages = messages[::-1]

        return messages


class KickHumanByCallsignRequest(ConsoleRequest):

    def __init__(
        self,
        callsign: str,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body=f"kick {callsign}",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )


class KickHumanByNumberRequest(ConsoleRequest):

    def __init__(
        self,
        number: int,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body=f"kick# {number}",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )


class ChatRequest(ConsoleRequest):

    def __init__(
        self,
        message: str,
        addressee: str,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body=f"chat {message} {addressee}",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )


class GetMissionInfoRequest(ConsoleRequest):

    def __init__(
        self,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body="mission",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )

    def _extract_result(self, messages: List[str]) -> structures.MissionInfo:
        messages = self._maybe_filter_messages(messages)
        message = messages[0]

        if message == "Mission NOT loaded":
            status = MissionStatuses.not_loaded
            file_path = None
        else:
            match = re.match(
                "Mission: (?P<file_path>.*) is (?P<status>.*)",
                message,
            )
            group = match.groupdict()

            file_path = group['file_path'].strip()
            status = (
                MissionStatuses.playing
                if group['status'] == "Playing"
                else MissionStatuses.loaded
            )

        return structures.MissionInfo(
            status=status,
            file_path=file_path,
        )

    @staticmethod
    def _maybe_filter_messages(messages: List[str]) -> List[str]:
        if not messages[0].startswith("Mission"):
            messages = messages[::-1]
            messages = list(takewhile(
                lambda s: not s.startswith("Mission"),
                messages,
            ))
            messages = messages[::-1]

        return messages


class MissionControlRequestBase(ConsoleRequest):

    def _extract_result(self, messages: List[str]) -> None:
        for message in messages:
            if message.startswith("ERROR mission"):
                details = message.split(':', 1)[1].strip()
                raise ConsoleRequestError(details)


class LoadMissionRequest(MissionControlRequestBase):

    def __init__(
        self,
        file_path: str,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body=f"mission LOAD {file_path}",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )


class BeginMissionRequest(MissionControlRequestBase):

    def __init__(
        self,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body="mission BEGIN",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )


class EndMissionRequest(MissionControlRequestBase):

    def __init__(
        self,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body="mission END",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )


class UnloadMissionRequest(MissionControlRequestBase):

    def __init__(
        self,
        timeout: Optional[float]=None,
        trace: bool=False,
        loop: asyncio.AbstractEventLoop=None,
    ):
        super().__init__(
            body="mission DESTROY",
            timeout=timeout,
            trace=trace,
            loop=loop,
        )
