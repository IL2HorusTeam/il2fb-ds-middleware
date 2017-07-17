# coding: utf-8

import logging

from typing import Optional

from .constants import ACTOR_INDEX_ERROR, ACTOR_STATUS_ERROR
from .structures import PreparsedActorPosition


LOG = logging.getLogger(__name__)


def actor_index_is_valid(
    item: PreparsedActorPosition,
) -> Optional[PreparsedActorPosition]:
    if item.data == ACTOR_INDEX_ERROR:
        LOG.error(f"invalid actor index (index={item.index})")
        return False

    return item


def actor_status_is_valid(
    item: PreparsedActorPosition,
) -> Optional[PreparsedActorPosition]:
    if item.data == ACTOR_STATUS_ERROR:
        LOG.error(f"invalid actor state (index={item.index})")
        return False

    return item
