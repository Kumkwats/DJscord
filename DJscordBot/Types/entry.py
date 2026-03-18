from dataclasses import dataclass
from enum import Enum

import discord

from DJscordBot.utils.io import get_file_duration

class EntryType(Enum):
    UNKNOWN = 0
    LOCAL_FILE = 1
    REMOTE = 2


@dataclass
class EntryFileData:
    filename: str
    path: str

    @property
    def is_available(self):
        if self.path.startswith(("http://", "https://", "udp://")):
            pass
        else:
            pass




class EntryPlaylist():
    """
    Class representing a playlist data for an entry.
    """
    def __init__(self, id, title: str, uploader: str, type, web_url: str):
        self.id: str = id
        self.title: str = title
        self.uploader: str = uploader
        self.type: str = type
        self.web_url: str = web_url


class Entry():
    """
    Class representing an entry in the queue.
    An entry can be a file or a stream.
    """
    def __init__(self, title: str, user: discord.User, web_url: str):
        #self.id = id
        self.title: str = title
        self.user: discord.User = user
        self.web_url: str = web_url

        self.is_ready = False

        self.playlist: EntryPlaylist = None

        self.description: str = ""
        self.image_link: str = None

        self.type: EntryType = EntryType.UNKNOWN

        # file
        self.filename: str = None
        self.duration: float = 0
        self.size = 0

        # stream
        self.remote_url: str = None

        self.is_saturated: bool = False
        self.is_reverse: bool = False

        self._is_boot_file: bool = False
        self._boot_file_path: str = ""

    def add_description(self, description):
        self.description = description

    def add_image(self, image_link):
        self.image_link = image_link

    def set_playlist(self, playlist: EntryPlaylist):
        self.playlist = playlist


    def map_to_file(self, filename: str, duration = 0, file_size = 0):
        self.type = EntryType.LOCAL_FILE
        self.filename = filename
        self.duration = duration
        self.size = file_size
        self.is_ready = True


    def map_to_remote(self, remote_url: str):
        self.type = EntryType.REMOTE
        self.remote_url = remote_url
        (_success, _duration, _) = get_file_duration(remote_url)
        if _success:
            self.duration = _duration
        self.is_ready = True

    



