# coding: utf-8

import functools

from typing import Tuple, Union

import inflect


INFLECT = inflect.engine()

StringOrBytes = Union[str, bytes]

plural_noun = INFLECT.plural_noun


@functools.lru_cache()
def _get_bounraries(max_length: int) -> Tuple[int, int]:
    div, mod = divmod(max_length, 2)

    left = div - 2
    right = div + mod - 3

    return (left, right)


def truncate(sequence: StringOrBytes, max_length: int=200) -> StringOrBytes:
    if len(sequence) <= max_length:
        return sequence
    else:
        left, right = _get_bounraries(max_length)
        return sequence[:left] + type(sequence)(" ... ") + sequence[-right:]
