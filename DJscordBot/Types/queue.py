import os
import time
import asyncio
import traceback

from enum import Enum

import discord

from DJscordBot.config import config
from DJscordBot.Types.entry import Entry
from DJscordBot.utils import time_format



class NextEntryCondition(Enum):
    DEFAULT = -1
    SEEK = 1
    SKIP = 2
    STOP = 3
    RESUME = 4

class RepeatMode(Enum):
    NO_REPEAT = 0
    ENTRY = 1
    PLAYLIST = 2
    ALL = 9




    




class Queue():
    def __init__(self, guild_id: int, voice_client: discord.VoiceClient, text_channel: discord.TextChannel):
        self.guild_id: int = guild_id
        self.content: list[Entry] = []
        
        self.size: int  = 0
        self.cursor: int = 0

        self.available_size: int = 0
        self.available_cursor: int = 0
        
        self.starttime = 0
        self.pausetime = 0
        
        self.last_voice_activity_time = time.time()
        self.__voice_client = voice_client
        self.text_channel = text_channel
        self.repeat_mode: RepeatMode = RepeatMode.NO_REPEAT # none, entry, playlist, all
        self.repeat_bypass: bool = False
        self.seek_time = -1
        self.is_other_source: bool = False
        self.next_entry_condition: NextEntryCondition = NextEntryCondition.DEFAULT

        # self.__is_processing_request = False


    #Voice Channel
    def get_voice_channel(self) -> discord.VoiceChannel:
        if not self.has_voice_client():
            print("[Queue.Get_Voice_Channel] voice_client is None")
            return None
        return self.__voice_client.channel
    
    def has_voice_client(self) -> bool:
        return self.__voice_client is not None
    

    #region Status
    def is_connected(self) -> bool:
        if not self.has_voice_client():
            print("[Queue.Is_Connected] voice_client is None")
            return False
        return self.__voice_client.is_connected()

    def is_playing(self) -> bool:
        if not self.has_voice_client():
            print("[Queue.Is_Playing] voice_client is None")
            return False
        return self.__voice_client.is_playing()
    
    def is_paused(self) -> bool:
        if not self.has_voice_client():
            print("[Queue.Is_Paused] voice_client is None")
            return False
        return self.__voice_client.is_paused()
    #endregion

    #region voice client functions
    def pause(self):
        if not self.has_voice_client():
            print("[Queue.Pause] voice_client is None")
            return
        self.__voice_client.pause()

    def pause(self):
        if not self.has_voice_client():
            print("[Queue.Resume] voice_client is None")
            return
        self.__voice_client.resume()

    def stop(self):
        if not self.has_voice_client():
            print("[Queue.Stop] voice_client is None")
            return
        self.__voice_client.stop()



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

    async def disconnect_and_cleanup(self):
        await self.__voice_client.disconnect()
        self.__voice_client.cleanup()
    #endregion





    def update_last_voice_activity(self) -> None:
        self.last_voice_activity_time = time.time()

    #Text Channel
    def check_text_channel(self, text_channel: discord.TextChannel) -> bool:
        #preventing typing commands in other text channels
        return self.text_channel == text_channel

    def move_text_channel(self, new_text_channel: discord.TextChannel):
        #change listening text channel
        self.text_channel = new_text_channel


    #Playback
    async def start_playback(self, timestart: int = 0, supress_output: bool = False):
        if not self.is_connected():
            print("[PLAYBACK.START.ERROR] Voice client is not connected, cannot start playback !")
            return await self.text_channel.send(f"Le Didjé a essayé de lancer une musique alors qu'il est apparemment pas connecté")

        if self.is_playing():
            print("[PLAYBACK.START.ERROR] Voice client is already, we won't start another playback !")
            return await self.text_channel.send(f"Le Didjé a essayé de lancer une musique alors qu'une autre est en cours")


        entry: Entry = self.content[self.cursor]
        if entry.size != 0:
            filename: str = config.downloadDirectory + entry.filename
            if not os.path.exists(filename):
                print("[PLAYBACK.START.ERROR] Attempting to play a file that doesn't exist !")
                await self.text_channel.send(f"Le Didjé a paumé le fichier de **{entry.title}**, on passe à la suivante du coup...")
                self.__on_after_play()
        else:
            filename: str = entry.filename
        

        
        

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
        
        self.__voice_client.play(
            player,
            after=lambda e: self.__on_after_play())
        
        self.starttime = time.time() - timestart

        if not supress_output:
            if timestart > 0:
                await self.text_channel.send(f"Déplacement du pointeur à **[{time_format(timestart)}]** dans la lecture en cours : {entry.title}")
            else:
                await self.text_channel.send(f"Maintenant en lecture : {entry.title}")

    def __on_after_play(self):
        if self.next_entry_condition is NextEntryCondition.SEEK:
            print(f"[QUEUE.AFTER_PLAY] on_after_play >> seek (GID:{self.guild_id})")
            return self.__play_seek()
        
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
        self.__play_next()

        self.next_entry_condition = NextEntryCondition.DEFAULT
        self.seek_time = -1
        self.repeat_bypass = False
        pass

    def __play_next(self):
        if self.repeat_bypass is False:
            if self.repeat_mode == RepeatMode.NO_REPEAT:
                self.cursor = self.cursor + 1
            elif self.repeat_mode == RepeatMode.ENTRY:
                pass
            elif self.repeat_mode == RepeatMode.ALL:
                if self.cursor == self.size - 1:
                    self.cursor = 0
                else:
                    self.cursor = self.cursor + 1
            elif self.repeat_mode == RepeatMode.PLAYLIST:
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
            fut = asyncio.run_coroutine_threadsafe(coro, self.__voice_client.loop)
            try:
                fut.result()
            except Exception:
                print(f"[ERROR] play_next(): a coroutine error occured (GID:{self.guild_id})\n\n{traceback.format_exc()}")


    def __play_seek(self):
        if self.seek_time < 0:
            return self.__play_next()
        # setting variables
        starting_time:int = self.seek_time

        # defaulting class variables for next uses
        self.seek_time = -1

        if self.cursor < self.size:
            coro = self.start_playback(timestart = starting_time)
            fut = asyncio.run_coroutine_threadsafe(coro, self.__voice_client.loop)
            try:
                fut.result()
            except Exception:
                print(f"[ERROR] play_seek(): a coroutine error occured (GID:{self.guild_id})\n\n{traceback.format_exc()}")




    async def add_entry(self, entry: Entry, position: int = None) -> int:
        
        if position is None or position == self.size:
            if not entry.is_ready:
                return -1
            self.content.append(entry)
        else:
            if not entry.is_ready:
                return -1
            self.content.insert(position, entry)

        self.size = self.size + 1
        if self.size == self.cursor + 1:
            await self.start_playback()

        return position or self.size-1

    def move_entry(self, frm: int, to: int):
        entry = self.content[frm]
        self.content.pop(frm)
        self.content.insert(to, entry)

    def remove_entry(self, index: int):
        self.content.pop(index)
        self.size = self.size - 1


    


    def get_index(self, entry: Entry) -> int:
        return self.content.index(entry)

    def get_entry(self, index: int) -> Entry:
        return self.content[index]
    

