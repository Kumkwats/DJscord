from enum import Enum


class RepeatMode(Enum):
    NONE = 0
    ENTRY = 1
    QUEUE = 2
    PLAYLIST = 3

class AfterEntryPlaybackAction(Enum):
    """
    Sets the action to perform after playback has stopped, either because the playback has ended or from a user's interaction (/stop, /seek, ...).
    """
    DEFAULT = -1
    SEEK = 1
    SKIP = 2
    STOP = 3
    RESUME = 4

class PlayQueryType(Enum):
    """
    Represents the type of query sent by the user.
    """
    UNHANDLED = -1
    SEARCH_QUERY = 0 # Youtube search query
    LINK_YOUTUBE = 1
    LINK_SPOTIFY = 3
    LINK_OTHER = 4 # Links that are not natively handled by the bot.
    FILE = 10 # File uploaded by the user.
    OTHER = 99

