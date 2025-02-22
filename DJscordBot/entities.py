import time
import asyncio
import traceback

from enum import Enum

import discord

from DJscordBot.utils import time_format
from DJscordBot.metadatas import YoutubeMetadata

from DJscordBot.config import config



class NextEntryCondition(Enum):
    DEFAULT = -1
    SEEK = 1
    SKIP = 2
    STOP = 3
    RESUME = 4





class Entry():
    def __init__(self, filename: str, applicant: discord.User, fileSize = 0, playlist = None):
        self.filename: str = filename
        self.file_size: int = fileSize
        
        self.applicant: discord.User = applicant

        self.is_youtube: bool = False
        self.youtube_metadata: YoutubeMetadata = None
        # self.is_spotify: bool = False
        # self.spotify_metadata: SpotifyMetadata = None
        self.playlist: Playlist = playlist


    def buildMetadataYoutube(self, data):
        self.is_youtube = True
        self.title = data['title']
        
        self.view_count = data['view_count']
        self.like_count = data['like_count']

        self.channel = data['channel']
        self.channel_url = data['channel_url']
        self.channel_follower_count = data['channel_follower_count']
        
        if 'album' in data:
            self.album = data['album']
        self.duration = data['duration'] if self.file_size != 0 else 0
        self.thumbnail = data['thumbnail']
        self.id = data['id']
        self.url = data['webpage_url']


    def BuildMetaDataOtherStreams(self, link: str):
        self.title = link
        self.url = link


class Playlist():
    def buildMetadataYoutube(self, data):
        self.title: str = data['title']
        self.uploader = data['uploader'] if 'uploader' in data else None
        self.id = data['id']
        self.url = data['webpage_url']

    # def buildMetadataSpotify(self, data):
    #     pass


class Queue():
    def __init__(self, guild_id: int, voice_client: discord.VoiceClient, text_channel: discord.TextChannel):
        self.guild_id: int = guild_id
        self.content: list[Entry] = []
        self.size = 0
        self.cursor = 0
        self.starttime = 0
        self.pausetime = 0
        self.last_voice_activity_time = time.time()
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.repeat_mode = "none"  # none, entry, playlist, all
        self.repeat_bypass = False
        self.seek_time = -1
        self.is_other_source: bool = False
        self.next_entry_condition: NextEntryCondition = NextEntryCondition.DEFAULT

    #Voice Channel
    def get_voice_channel(self) -> discord.VoiceChannel:
        return self.voice_client.channel

    #Voice Client
    def is_connected(self) -> bool:
        return self.voice_client.is_connected()

    def is_playing(self) -> bool:
        return self.voice_client.is_playing()

    def stop(self) -> None:
        self.voice_client.stop()

    async def connect(self, voice_channel: discord.VoiceChannel) -> None:
        self.voice_client = await voice_channel.connect(timeout=600, reconnect=True)
        
    async def reconnect(self) -> None:
        self.voice_client = await self.voice_client.channel.connect(timeout=600, reconnect=True)

    async def move(self, new_voice_channel: discord.VoiceChannel) -> None:
        await self.voice_client.move_to(new_voice_channel)

    async def disconnect(self) -> None:
        await self.voice_client.disconnect()

    def voice_activity_update(self) -> None:
        self.last_voice_activity_time = time.time()

    #Text Channel
    def check_text_channel(self, text_channel: discord.TextChannel) -> bool:
        #preventing typing commands in other text channels
        return self.text_channel == text_channel

    def move_text_channel(self, new_text_channel: discord.TextChannel) -> None:
        #change listening text channel
        self.text_channel = new_text_channel


    #Playback
    async def start_playback(self, timestart: int = 0, supress_output: bool = False):
        if self.voice_client.is_connected() and not self.voice_client.is_playing():
            entry: Entry = self.content[self.cursor]
            filename: str = config.downloadDirectory + entry.filename if entry.file_size != 0 else entry.filename

            #seek parameters
            before: str = ""
            if timestart > 0:
                before = f"-ss {timestart}"
            else:
                timestart = 0

            player: discord.FFmpegPCMAudio = discord.FFmpegPCMAudio(
                filename,
                before_options = before,
                options = "-vn")
            
            self.voice_client.play(
                player,
                after=lambda e: self.on_after_play())
            
            self.starttime = time.time() - timestart

            if not supress_output:
                if timestart > 0:
                    await self.text_channel.send(f"Déplacement du pointeur à **[{time_format(timestart)}]** dans la lecture en cours : {entry.title}")
                else:
                    await self.text_channel.send(f"Maintenant en lecture : {entry.title}")

    def on_after_play(self):
        if self.next_entry_condition is NextEntryCondition.SEEK:
            print(f"[QUEUE.AFTER_PLAY] on_after_play >> seek (GID:{self.guild_id})")
            return self.play_seek()
        # elif self.next_entry_condition is NextEntryCondition.SKIP:
        #     self.cursor
        elif self.next_entry_condition is NextEntryCondition.STOP:
            
            #restore to defaults
            self.next_entry_condition = NextEntryCondition.DEFAULT
            self.seek_time = -1
            self.repeat_bypass = False

            print(f"[QUEUE.AFTER_PLAY] on_after_play >> stop (GID:{self.guild_id})")
            return
        # elif self.next_entry_condition is NextEntryCondition.RESUME:
        #     pass
        
        print(f"[QUEUE.AFTER_PLAY] on_after_play >> next entry (GID:{self.guild_id})")
        self.play_next()

        self.next_entry_condition = NextEntryCondition.DEFAULT
        self.seek_time = -1
        self.repeat_bypass = False
        pass

    def play_next(self):
        if self.repeat_bypass is False:
            if self.repeat_mode == "none":
                self.cursor = self.cursor + 1
            elif self.repeat_mode == "entry":
                pass
            elif self.repeat_mode == "all":
                if self.cursor == self.size - 1:
                    self.cursor = 0
                else:
                    self.cursor = self.cursor + 1
            elif self.repeat_mode == "playlist":
                def gotostart():
                    i = self.cursor-1
                    while self.content[i].playlist is not None and i >= 0:
                        if self.content[i].playlist.id == current_entry.playlist.id:
                            i = i-1
                        else:
                            break
                    self.cursor = i

                current_entry = self.content[self.cursor]
                if current_entry.playlist.id is not None:
                    if self.cursor < self.size-1:
                        if self.content[self.cursor+1].playlist is not None:
                            if self.content[self.cursor+1].playlist.id != current_entry.playlist.id:
                                gotostart()
                        else:
                            gotostart()
                    elif self.cursor == self.size - 1:
                        gotostart()

                self.cursor = self.cursor + 1

        # defaulting class variables for next uses
        self.seek_time = -1
        self.repeat_bypass = False
        if self.cursor < self.size:
            coro = self.start_playback()
            fut = asyncio.run_coroutine_threadsafe(coro, self.voice_client.loop)
            try:
                fut.result()
            except Exception:
                print(f"[ERROR] play_next(): a coroutine error occured (GID:{self.guild_id})\n\n{traceback.format_exc()}")

    def play_seek(self):
        if self.seek_time < 0:
            return self.play_next()
        # setting variables
        starting_time:int = self.seek_time

        # defaulting class variables for next uses
        self.seek_time = -1

        if self.cursor < self.size:
            coro = self.start_playback(timestart = starting_time)
            fut = asyncio.run_coroutine_threadsafe(coro, self.voice_client.loop)
            try:
                fut.result()
            except Exception:
                print(f"[ERROR] play_seek(): a coroutine error occured (GID:{self.guild_id})\n\n{traceback.format_exc()}")


    # def play_other(self):
    #     if self.is_playing:
    #         self.is_other_source = True

    async def add_entry(self, entry: Entry, position=None) -> int:
        if position is None or position == self.size:
            self.content.append(entry)
        else:
            self.content.insert(position, entry)
        self.size = self.size + 1
        if self.size == self.cursor + 1:
            await self.start_playback()

        return position or self.size-1

    def remove_entry(self, index: int):
        self.content.pop(index)
        self.size = self.size - 1

    def move_entry(self, frm: int, to: int):
        entry = self.content[frm]
        self.content.pop(frm)
        self.content.insert(to, entry)

    def get_index(self, entry: Entry) -> int:
        return self.content.index(entry)

    def get_entry(self, index: int) -> Entry:
        return self.content[index]
    

