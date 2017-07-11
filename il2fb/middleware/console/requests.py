# coding: utf-8

import asyncio
import itertools
import logging
import re

from typing import Any, List, Callable

from il2fb.commons import MissionStatuses
from il2fb.commons.organization import Belligerents

from . import structures
from .exceptions import ConsoleRequestError


LOG = logging.getLogger(__name__)


class ConsoleRequest:

    def __init__(self, future: asyncio.Future, body: str) -> None:
        self.body = body
        self._future = future

    def set_result(self, result: Any) -> None:
        try:
            self._future.set_result(result)
        except asyncio.futures.InvalidStateError:
            LOG.error(
                f"failed to set request result "
                f"(request={self}, future={self.future}, result={result})"
            )

    def set_exception(self, e: Exception) -> None:
        try:
            self._future.set_exception(e)
        except asyncio.futures.InvalidStateError:
            LOG.error(
                f"failed to set request exception "
                f"(request={self}, future={self.future}, e={e})"
            )

    def add_done_callback(self, cb: Callable[[asyncio.Future], None]) -> None:
        self._future.add_done_callback(cb)

    def __str__(self) -> str:
        return self.body

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self.body}')>"


class ServerInfoRequest(ConsoleRequest):

    def __init__(self, future: asyncio.Future) -> None:
        super().__init__(future=future, body="server")

    def set_result(self, messages: List[str]) -> None:
        messages = list(map(
            lambda x: x.split(':', 1)[1].strip(),
            messages,
        ))
        result = structures.ServerInfo(
            type=messages[0],
            name=messages[1],
            description=messages[2],
        )
        super().set_result(result)


class UserListRequest(ConsoleRequest):

    def __init__(self, future: asyncio.Future) -> None:
        super().__init__(future=future, body="user")

    def set_result(self, messages: List[str]) -> None:
        users = []

        for message in messages[1:]:
            data = re.split('\s{2,}', message.strip())[1:]

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

            user = structures.User(
                callsign=callsign,
                ping=ping,
                score=score,
                belligerent=belligerent,
                aircraft=aircraft,
            )
            users.append(user)

        super().set_result(users)


class UserStatisticsRequest(ConsoleRequest):

    def __init__(self, future: asyncio.Future) -> None:
        super().__init__(future=future, body="user STAT")

    def set_result(self, messages: List[str]) -> None:
        stats = []
        field_names = itertools.cycle(structures.UserStatistics.__slots__)
        buffer = {}

        for message in messages[1:]:
            if message.startswith('-'):
                item = structures.UserStatistics(**buffer)
                stats.append(item)
                continue

            field_name = next(field_names)
            value = message.replace('\\t', '').split(': ')[1]

            if field_name not in {'callsign', 'state'}:
                value = int(value)

            buffer[field_name] = value

        super().set_result(stats)


class KickByCallsignRequest(ConsoleRequest):

    def __init__(self, future: asyncio.Future, callsign: str) -> None:
        super().__init__(
            body=f"kick {callsign}",
            future=future,
        )

    def set_result(self, messages: List[str]) -> None:
        super().set_result(None)


class KickByNumberRequest(ConsoleRequest):

    def __init__(self, future: asyncio.Future, number: int) -> None:
        super().__init__(
            body=f"kick# {number}",
            future=future,
        )

    def set_result(self, messages: List[str]) -> None:
        super().set_result(None)


class ChatRequest(ConsoleRequest):

    def __init__(
        self,
        future: asyncio.Future,
        message: str,
        target: str,
    ) -> None:
        super().__init__(
            body=f"chat {message} {target}",
            future=future,
        )

    def set_result(self, messages: List[str]) -> None:
        super().set_result(None)


class MissionStatusRequest(ConsoleRequest):

    def __init__(self, future: asyncio.Future) -> None:
        super().__init__(future=future, body="mission")

    def set_result(self, messages: List[str]) -> None:
        message = messages[0]

        if message == "Mission NOT loaded":
            status = MissionStatuses.not_loaded
            file_path = None
        else:
            match = re.match(
                "Mission: (?P<file_path>.*) is (?P<status>.*)", message,
            )
            group = match.groupdict()

            file_path = group['file_path'].strip()
            status = (
                MissionStatuses.playing
                if group['status'] == "Playing"
                else MissionStatuses.loaded
            )

        result = structures.MissionInfo(status=status, file_path=file_path)
        super().set_result(result)


class MissionControlRequestBase(ConsoleRequest):

    def set_result(self, messages: List[str]) -> None:
        for message in messages:
            if message.startswith('ERROR mission'):
                message = message.split(':', 1)[1].strip()
                super().set_exception(ConsoleRequestError(message))
                return

        super().set_result(None)


class MissionLoadRequest(MissionControlRequestBase):

    def __init__(self, future: asyncio.Future, file_path: str) -> None:
        super().__init__(future=future, body=f"mission LOAD {file_path}")


class MissionBeginRequest(MissionControlRequestBase):

    def __init__(self, future: asyncio.Future) -> None:
        super().__init__(future=future, body="mission BEGIN")


class MissionEndRequest(MissionControlRequestBase):

    def __init__(self, future: asyncio.Future) -> None:
        super().__init__(future=future, body="mission END")


class MissionDestroyRequest(MissionControlRequestBase):

    def __init__(self, future: asyncio.Future) -> None:
        super().__init__(future=future, body="mission DESTROY")
