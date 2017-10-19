# coding: utf-8

from typing import Optional

from il2fb.commons.events import ParsableEvent
from il2fb.commons.regex import (
    ANYTHING, WHITESPACE, DIGIT, NUMBER, START_OF_STRING, END_OF_STRING,
    make_matcher, choices, group, named_group,
)
from il2fb.commons.transformers import get_int_transformer

from .constants import CHAT_SENDER_SERVER, CHAT_SENDER_SYSTEM


IP_REGEX = "({d}{{1,3}}.){{3}}{d}{{1,3}}".format(d=DIGIT)


def transform_chat_body(data):
    data['body'] = data['body'].encode().decode('unicode-escape')


def transform_chat_sender(data):
    sender = data.get('sender')

    if sender:
        sender = sender.encode().decode('unicode-escape')

    data['sender'] = sender


class ChatMessageWasReceived(ParsableEvent):
    """
    Examples:

        "Chat: --- hello everyone"
        "Chat: Server: \thello everyone"
        "Chat: john.doe: \thello everyone"

    """
    __slots__ = ['body', 'sender', 'from_user', 'from_server', 'from_system', ]

    verbose_name = "Chat message was received"
    matcher = make_matcher(
        "{start}Chat:{s}{sender_with_separator}{body}{end}"
        .format(
            start=START_OF_STRING,
            s=WHITESPACE,
            end=END_OF_STRING,
            sender_with_separator=group(choices([
                group(
                    "{sender}:{s}\\t"
                    .format(
                        sender=named_group('sender', ANYTHING),
                        s=WHITESPACE,
                    )
                ),
                (
                    "{system}{s}"
                    .format(
                        system=CHAT_SENDER_SYSTEM,
                        s=WHITESPACE,
                    )
                ),
            ])),
            body=named_group('body', ANYTHING),
        )
    )
    transformers = (
        transform_chat_body,
        transform_chat_sender,
    )

    def __init__(self, body: str, sender: Optional[str]=None):
        from_system = (sender is None)
        from_server = (
            (not from_system) and
            (sender == CHAT_SENDER_SERVER)
        )
        from_user = not (from_server or from_system)

        sender = (sender if from_user else None)

        super().__init__(
            body=body,
            sender=sender,
            from_user=from_user,
            from_server=from_server,
            from_system=from_system,
        )


class UserIsJoining(ParsableEvent):
    """
    Example:

        "socket channel '3' start creating: 127.0.0.1:1234"

    """
    __slots__ = ['channel', 'ip', 'port', ]

    verbose_name = "User is joining"
    matcher = make_matcher(
        "{start}socket{s}channel{s}'{channel}'{s}start{s}creating:{s}{ip}:{port}{end}"
        .format(
            start=START_OF_STRING,
            s=WHITESPACE,
            channel=named_group('channel', NUMBER),
            ip=named_group('ip', IP_REGEX),
            port=named_group('port', NUMBER),
            end=END_OF_STRING,
        )
    )
    transformers = (
        get_int_transformer('channel'),
        get_int_transformer('port'),
    )


class UserHasJoined(ParsableEvent):
    """
    Example:

        "socket channel '3', ip 127.0.0.1:1234, john.doe, is complete created"

    """
    __slots__ = ['channel', 'ip', 'port', 'callsign', ]

    verbose_name = "User has joined"
    matcher = make_matcher(
        "{start}socket{s}channel{s}'{channel}',{s}ip{s}{ip}:{port},{s}"
        "{callsign},{s}is{s}complete{s}created{end}"
        .format(
            start=START_OF_STRING,
            s=WHITESPACE,
            channel=named_group('channel', NUMBER),
            ip=named_group('ip', IP_REGEX),
            port=named_group('port', NUMBER),
            callsign=named_group('callsign', ANYTHING),
            end=END_OF_STRING,
        )
    )
    transformers = (
        get_int_transformer('channel'),
        get_int_transformer('port'),
    )


def transform_disconnection_reason(data):
    reason = data['reason']

    if not reason:
        data['reason'] = None


class UserHasLeft(ParsableEvent):
    """
    Example:

        "socketConnection with 127.0.0.1:1234 on channel 3 lost.  Reason: "
        "socketConnection with 127.0.0.1:4567 on channel 5 lost.  Reason: Timeout"

    """
    __slots__ = ['channel', 'ip', 'port', 'reason', ]

    verbose_name = "User has left"
    matcher = make_matcher(
        "{start}socketConnection{s}with{s}{ip}:{port}{s}on{s}channel{s}"
        "{channel}{s}lost.{s}{s}Reason:{s}{reason}{end}"
        .format(
            start=START_OF_STRING,
            s=WHITESPACE,
            ip=named_group('ip', IP_REGEX),
            port=named_group('port', NUMBER),
            channel=named_group('channel', NUMBER),
            reason=named_group('reason', ".*"),
            end=END_OF_STRING,
        )
    )
    transformers = (
        get_int_transformer('channel'),
        get_int_transformer('port'),
        transform_disconnection_reason,
    )
