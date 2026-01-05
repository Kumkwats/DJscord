from dataclasses import dataclass
from enum import Flag, auto

import discord

from .common import ObjectUID


@dataclass
class DiscordData:
    applicant: discord.User


@dataclass
class EmbedData:
    description: str
    image_link: str


@dataclass
class PlaylistData():
    """
    Class representing a playlist data for an entry.
    """
    id: ObjectUID
    title: str
    uploader: str
    type: str
    web_url: str



class AudioModifier(Flag):
    SATURATED = auto()
    REVERSED = auto()



@dataclass
class QEntry:
    entry_id: ObjectUID
    discord_data: DiscordData
    embed_data: EmbedData
    playlist: PlaylistData

    audio_modifiers: AudioModifier


@dataclass
class QueuePlayerData:
    start_time: int
    pause_time: int

class Queue():
    """
    Class representing a queue of entries to be played in a Discord guild's voice channel.
    With functions to manage the queue, playback, and voice channel.
    """
    def __init__(self):
        self.entries: list[QEntry]
        self.size: int = 0
        self.cursor: int = 0

    pass


