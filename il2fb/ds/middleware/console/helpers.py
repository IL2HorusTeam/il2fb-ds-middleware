# coding: utf-8

import re

from .constants import KNOWN_COMMANDS


def is_unknown_command(s: str) -> bool:
    return s.startswith("Command not found:")


def is_user_input(s: str) -> bool:
    first_word = s.split()[0]
    for known_command in KNOWN_COMMANDS:
        if first_word == known_command or is_unknown_command(s):
            return True

    return False


def is_server_input(s: str) -> bool:
    return s.startswith('>')


def is_command_prompt(s: str) -> bool:
    return re.match(r"^<consoleN><\d+>$", s) is not None


def is_command_prompt_continuation(s: str) -> bool:
    return re.match(r"^\d+>$", s) is not None
