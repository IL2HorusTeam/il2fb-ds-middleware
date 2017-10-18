# coding: utf-8

import re

from typing import Dict, Union, Optional


USER_IS_JOINING_REGEX = (
    r"^socket channel '(?P<channel>\d+)' start creating: "
    r"(?P<ip>(\d{1,3}.){3}\d{1,3}):(?P<port>\d+)$"
)

USER_HAS_JOINED_REGEX = (
    r"^socket channel '(?P<channel>\d+)', ip "
    r"(?P<ip>(\d{1,3}.){3}\d{1,3}):(?P<port>\d+), "
    "(?P<callsign>.+), is complete created$"
)

USER_HAS_LEFT_REGEX = (
    r"^socketConnection with (?P<ip>(\d{1,3}.){3}\d{1,3}):(?P<port>\d+) "
    r"on channel (?P<channel>\d+) lost.  Reason: (?P<reason>.*)$"
)


def parse_user_is_joining(s: str) -> Optional[
    Dict[str, Union[int, str]]
]:
    match = re.match(USER_IS_JOINING_REGEX, s)

    if not match:
        return

    result = match.groupdict()
    result['port'] = int(result['port'])
    result['channel'] = int(result['channel'])

    return result


def parse_user_has_joined(s: str) -> Optional[
    Dict[str, Union[int, str]]
]:
    match = re.match(USER_HAS_JOINED_REGEX, s)

    if not match:
        return

    result = match.groupdict()
    result['callsign'] = result['callsign'].encode().decode('unicode-escape')
    result['port'] = int(result['port'])
    result['channel'] = int(result['channel'])

    return result


def parse_user_has_left(s: str) -> Optional[
    Dict[str, Union[int, str]]
]:
    match = re.match(USER_HAS_LEFT_REGEX, s)

    if not match:
        return

    result = match.groupdict()
    result['port'] = int(result['port'])
    result['channel'] = int(result['channel'])

    reason = result['reason']
    if not reason:
        result['reason'] = None

    return result
