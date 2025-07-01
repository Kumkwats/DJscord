from enum import Enum


class RepeatMode(Enum):
    NONE = 0
    ENTRY = 1
    QUEUE = 2
    PLAYLIST = 3

class NextEntryCondition(Enum):
    DEFAULT = -1
    SEEK = 1
    SKIP = 2
    STOP = 3
    RESUME = 4

class PlayQueryType(Enum):
    UNHANDLED = -1
    SEARCH_QUERY = 0
    LINK_YOUTUBE = 1
    LINK_SPOTIFY = 3
    OTHER_STREAM = 99

