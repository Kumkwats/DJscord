from dataclasses import dataclass
from enum import Flag, auto

from .common import ObjectUID

import discord


@dataclass
class EntryMediaData:
    title: str
    duration: float
    # is_live: bool

@dataclass
class EntryFileData:
    file_name: str
    file_size: int


@dataclass
class Entry:
    """
    Class representing an entry in the queue.
    An entry can be a file or a stream.
    """
    id: ObjectUID
    media_data: EntryMediaData
    file_data: EntryFileData

