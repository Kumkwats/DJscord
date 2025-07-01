from enum import Enum

import discord



class EntryType(Enum):
    UNKNOWN = 0
    FILE = 1
    STREAM = 2


class EntryPlaylist():
    def __init__(self, id, title: str, uploader: str, type, web_url: str):
        self.id = id
        self.title: str = title
        self.uploader: str = uploader
        self.type: str = type
        self.web_url: str = web_url


class Entry():
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
        self.duration = 0
        self.size = 0

        # stream
        self.stream_link: str = None

        

    def add_description(self, description):
        self.description = description

    def add_image(self, image_link):
        self.image_link = image_link

    def set_playlist(self, playlist: EntryPlaylist):
        self.playlist = playlist


    def map_to_file(self, filename: str, duration = 0, file_size = 0):
        self.type = EntryType.FILE
        self.filename = filename
        self.duration = duration
        self.size = file_size
        self.is_ready = True


    def map_to_stream(self, stream_url: str):
        self.type = EntryType.STREAM
        self.stream_link = stream_url
        self.is_ready = True

    



