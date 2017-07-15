# coding: utf-8

import re

from typing import List

from .messages import DeviceLinkMessage
from .constants import (
    MESSAGE_SEPARATOR, TYPE_REQUEST, TYPE_SEPARATOR, VALUE_SEPARATOR,
)


def compose_request(messages: List[DeviceLinkMessage]) -> str:
    body = MESSAGE_SEPARATOR.join([str(m) for m in messages])
    return f"{TYPE_REQUEST}{TYPE_SEPARATOR}{body}"


def decompose_response(response: str) -> List[DeviceLinkMessage]:
    payload = response[2:]

    results = []

    for chunk in payload.split(MESSAGE_SEPARATOR):
        command = chunk.split(VALUE_SEPARATOR)
        opcode = int(command[0])
        arg = command[1:]
        arg = arg[0] if arg else None
        message = DeviceLinkMessage(opcode, arg)
        results.append(message)

    return results


def normalize_aircraft_id(s: str) -> str:
    m = re.match(r"(.*?)(?:_\d+|$)", s)
    return m.groups()[0]
