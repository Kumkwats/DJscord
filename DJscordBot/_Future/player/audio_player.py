import time
from enum import Enum, Flag, auto

import discord


from ..datatypes.queue import Queue

class PlayerState(Flag):
    PLAYING = auto()
    PAUSED = auto()
    REPEAT = auto()
    

class RepeatMode(Enum):
    NONE = 0
    ENTRY = 1
    QUEUE = 2
    PLAYLIST = 3

class AfterPlayAction(Enum):
    """
    Sets the action to perform after playback has stopped, either because the playback has ended or from a user's interaction (/stop, /seek, ...).
    """
    DEFAULT = -1
    SEEK = 1
    SKIP = 2
    STOP = 3
    RESUME = 4



class AudioPlayer:
    def __init__(self, guild_id):
        self.guild_id: int = guild_id
        self.__state: PlayerState = PlayerState(0)
        self.queue: Queue = Queue()

        self.start_time: int = time.time()
        self.pause_time: int = time.time()

        self.next_entry_action: AfterPlayAction = AfterPlayAction.DEFAULT
        self.repeat_mode: RepeatMode = RepeatMode.NONE # none, entry, playlist, all
        self.dont_update_cursor_position: bool = False

        self.__last_voice_activity_time: int = time.time()
        # self.__voice_client: discord.VoiceClient = None
        self.__text_channel: discord.TextChannel = None

    @property
    async def __voice_client(self):
        
        



    async def connect(self, voice_channel: discord.VoiceChannel):
        if self.__voice_client is None:
            self.__voice_client = await voice_channel.connect(timeout=60)
        else:
            self.__voice_client = await voice_channel.connect(timeout=60, cls=self.__voice_client)

    async def reconnect(self) -> bool:
        if self.__voice_client is None:
            return False
        self.__voice_client = await self.__voice_client.channel.connect(timeout=60, cls=self.__voice_client)
        return True
    
    async def move(self, new_voice_channel: discord.VoiceChannel):
        await self.__voice_client.move_to(new_voice_channel)
