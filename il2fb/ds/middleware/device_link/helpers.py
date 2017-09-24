# coding: utf-8

import re

from typing import List, Tuple, Optional

from .constants import (
    REQUEST_PREFIX, ANSWER_PREFIX, MESSAGE_SEPARATOR, VALUE_SEPARATOR,
)
from .exceptions import DeviceLinkValueError
from .messages import DeviceLinkMessage, make_message


def decompose_data(data: bytes) -> List[DeviceLinkMessage]:
    if not (data.startswith(REQUEST_PREFIX) or data.startswith(ANSWER_PREFIX)):
        raise DeviceLinkValueError(f"malformed device link data {data}")

    data = data[2:]  # strip prefix

    if b'\\/' in data:
        chunks = re.findall(b'(\d+\\\\\d+:.+?(?:;\d+)+)', data)
    else:
        chunks = data.split(MESSAGE_SEPARATOR)

    args_list = map(parse_data, chunks)

    return [
        make_message(*args)
        for args in args_list
    ]


def parse_data(data: bytes) -> Tuple[int, Optional[str]]:
    if VALUE_SEPARATOR in data:
        opcode, value = data.split(VALUE_SEPARATOR, 1)
        value = value.decode().replace('\\/', '/').replace('\\\\', '\\')
    else:
        opcode, value = data, None

    opcode = int(opcode)
    return (opcode, value)


def compose_body(messages: List[DeviceLinkMessage]) -> bytes:
    return MESSAGE_SEPARATOR.join([msg.to_bytes() for msg in messages])


def compose_request(messages: List[DeviceLinkMessage]) -> bytes:
    return REQUEST_PREFIX + compose_body(messages)


def compose_answer(messages: List[DeviceLinkMessage]) -> bytes:
    return ANSWER_PREFIX + compose_body(messages)


def normalize_aircraft_id(s: str) -> str:
    m = re.match(r"(.*?)(?:_\d+|$)", s)
    return m.groups()[0]
