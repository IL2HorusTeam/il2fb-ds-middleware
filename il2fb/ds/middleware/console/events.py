# coding: utf-8

from typing import Optional

from il2fb.commons.events import ParsableEvent
from il2fb.commons.regex import (
    ANYTHING, WHITESPACE, START_OF_STRING, END_OF_STRING,
    make_matcher, choices, group, named_group,
)

from .constants import CHAT_SENDER_SERVER, CHAT_SENDER_SYSTEM


def transform_chat_body(data):
    data['body'] = data['body'].encode().decode('unicode-escape')


def transform_chat_sender(data):
    sender = data.get('sender')

    if sender:
        sender = sender.encode().decode('unicode-escape')

    data['sender'] = sender


class ChatMessageWasReceived(ParsableEvent):
    __slots__ = ['body', 'sender', 'from_user', 'from_server', 'from_system', ]

    verbose_name = "Chat message was received"
    matcher = make_matcher(
        r"{start}Chat:{s}{sender_with_separator}{body}{end}"
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
