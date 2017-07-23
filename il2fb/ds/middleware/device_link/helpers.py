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
    response = response[2:]

    if '\\/' in response:
        responses = re.findall('(\d+\\\\\d+:.+?(?:;\d+)+)', response)
    else:
        responses = response.split(MESSAGE_SEPARATOR)

    return list(map(response_to_message, responses))


def response_to_message(response):
    command = response.split(VALUE_SEPARATOR, 1)
    opcode = int(command[0])
    arg = command[1:]
    arg = arg[0].replace('\\/', '/').replace('\\\\', '\\') if arg else None
    return DeviceLinkMessage(opcode, arg)


def normalize_aircraft_id(s: str) -> str:
    m = re.match(r"(.*?)(?:_\d+|$)", s)
    return m.groups()[0]
