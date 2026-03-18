import os
import random
import time
import asyncio
import traceback

import discord


from ..config import config
from ..client import DJscordClient
from ..utils.format import time_format
from ..utils.io import get_file_duration, pick_sound_file

from .entry import Entry, EntryType
from .enums import RepeatMode, AfterEntryPlaybackAction

from ..logging.utils import get_logger
logger = get_logger("djscordbot.queue")



    




class Queue():
    """
    Class representing a queue of entries to be played in a Discord guild's voice channel.
    With functions to manage the queue, playback, and voice channel.

    """
    def __init__(self, guild_id: int, voice_client: discord.VoiceClient, text_channel: discord.TextChannel):
        self.guild_id: int = guild_id
        self.entries: list[Entry] = []
        
        self.stopped: bool = True

        self.size: int  = 0
        self.cursor: int = 0

        self.available_size: int = 0
        self.available_cursor: int = 0
        
        self.starttime = 0
        self.pausetime = 0
        
        self.last_voice_activity_time = time.time()
        self.__voice_client = voice_client
        self.text_channel = text_channel

        self.repeat_mode: RepeatMode = RepeatMode.NONE # none, entry, playlist, all
        self.dont_update_cursor_position: bool = False

        self.seek_time = -1
        self.is_other_source: bool = False
        
        self.next_entry_condition: AfterEntryPlaybackAction = AfterEntryPlaybackAction.DEFAULT

        # self.__is_processing_request = False


    
            
    @property
    def current_entry_index(self) -> int:
        if not self.ended and not self.stopped:
            return self.cursor

    @property
    def current_playing_entry(self) -> Entry:
        if not self.ended and not self.stopped:
            return self.entries[self.cursor]
    


    #region Voice
    @property
    def has_voice_client(self) -> bool:
        return self.__voice_client is not None

    @property
    def voice_channel(self) -> discord.VoiceChannel:
        if not self.has_voice_client:
            logger.error(f"[GET_VOICE_CHANNEL] voice_client is None (GID:{self.guild_id})")
            return None
        return self.__voice_client.channel
    #endregion
    

    #region Status
    @property
    def is_connected(self) -> bool:
        if not self.has_voice_client:
            logger.error(f"[IS_CONNECTED] voice_client is None (GID:{self.guild_id})")
            return False
        return self.__voice_client.is_connected()

    @property
    def is_playing(self) -> bool:
        if not self.has_voice_client:
            logger.error(f"[IS_PLAYING] voice_client is None (GID:{self.guild_id})")
            return False
        return self.__voice_client.is_playing()
    
    @property
    def is_paused(self) -> bool:
        if not self.has_voice_client:
            logger.error(f"[IS_PAUSED] voice_client is None (GID:{self.guild_id})")
            return False
        return self.__voice_client.is_paused()
    
    @property
    def ended(self) -> bool:
        return self.cursor >= self.size
    #endregion

    #region voice client functions
    def pause(self):
        if not self.has_voice_client:
            logger.error(f"[PAUSE] voice_client is None (GID:{self.guild_id})")
            return
        self.__voice_client.pause()

    def resume(self):
        if not self.has_voice_client:
            logger.error(f"[RESUME] voice_client is None (GID:{self.guild_id})")
            return
        self.__voice_client.resume()

    #TODO ERRORS
    #- Stop doesn't really stop
    def stop(self):
        if not self.has_voice_client:
            logger.error(f"[STOP] voice_client is None (GID:{self.guild_id})")
            return
        self.__voice_client.stop()




    async def connect(self, voice_channel: discord.VoiceChannel):
        self.__voice_client = await voice_channel.connect(timeout=60)

    # async def reconnect(self) -> bool:
    #     if self.__voice_client is None:
    #         logger.error(f"[QUEUE.RECONNECT] Cannot reconnect because voice client is None (GID:{self.guild_id})\n\tException: '{toErr}'")
    #         return False
    #     try:
    #         self.__voice_client = await self.__voice_client.channel.connect(timeout=60)
    #     except asyncio.TimeoutError as toErr:
    #         logger.error(f"[QUEUE.RECONNECT.TIMEOUT] connect timed out... (GID:{self.guild_id})\n\tException: '{toErr}'")
    #         return False
    #     except discord.ClientException as cEx:
    #         logger.error(f"[QUEUE.RECONNECT.CLIENT] unable to connect to VC because it is already connected to a voice client... (GID:{self.guild_id})")
    #         return False
    #     return True


    async def move(self, new_voice_channel: discord.VoiceChannel):
        await self.__voice_client.move_to(new_voice_channel, timeout=60)

    async def disconnect(self):
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


    #audio boot sequence
    async def boot(self, bot_user: DJscordClient):
        boot_entry: Entry = self.__create_boot_entry(bot_user)


        if config.allow_startup_filters:
            if random.random() < 0.01 :
                boot_entry.is_saturated = True
                boot_entry.title = boot_entry.title.upper()
            if random.random() < 0.01 :
                boot_entry.is_reverse = True
                boot_entry.title = boot_entry.title[::-1]

        if boot_entry is not None:
            await self.add_entry(boot_entry)
        pass

    def __create_boot_entry(self, bot_user: DJscordClient) -> Entry | None:
        check, file = pick_sound_file("startup")
        if check:
            if file != "":
                new_entry = Entry("Booting up...", bot_user.user, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                new_entry.add_image("https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/3ddaa372-c58c-4587-911e-1d625dff64dc/dapv26n-b138c16c-1cfc-45c3-9989-26fcd75d3060.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3sicGF0aCI6IlwvZlwvM2RkYWEzNzItYzU4Yy00NTg3LTkxMWUtMWQ2MjVkZmY2NGRjXC9kYXB2MjZuLWIxMzhjMTZjLTFjZmMtNDVjMy05OTg5LTI2ZmNkNzVkMzA2MC5qcGcifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6ZmlsZS5kb3dubG9hZCJdfQ.PnU42OFMHcio7nJ4a5Jsp8C-d6exHqd3vInU1682x1E")
                new_entry.add_description("Chaîne : [DJPatrice](https://github.com/Kumkwats/DJscord)")
                (_success, _duration, _) = get_file_duration(file)
                new_entry.map_to_file(file, _duration)
                new_entry._is_boot_file = True
                new_entry._boot_file_path = file
                logger.debug(f"[STARTUP] startup file added to queue")
                return new_entry
            else:
                logger.debug(f"[STARTUP] no startup file found")
        else:
            logger.debug(f"[STARTUP] sounds folder not found")

##warning  FFMPEG args for multiple stream at different time : https://stackoverflow.com/questions/37297856/ffmpeg-combine-video-files-with-different-start-times


    #Playback
    async def start_playback(self, timestart: int = 0, supress_output: bool = False):
        if not self.is_connected:
            logger.error(f"[PLAYBACK.START] Voice client is not connected, cannot start playback! (GID:{self.guild_id})")
            return await self.text_channel.send(f"Le Didjé a essayé de lancer une musique alors qu'il est apparemment pas connecté")

        if self.is_playing:
            logger.error(f"[PLAYBACK.START] Voice client is already, we won't start another playback! (GID:{self.guild_id})")
            return await self.text_channel.send(f"Le Didjé a essayé de lancer une musique alors qu'une autre est en cours")


        entry: Entry = self.entries[self.cursor]
        match entry.type:

            case EntryType.LOCAL_FILE:
                if entry._is_boot_file:
                    file_path: str = entry._boot_file_path
                else:
                    file_path: str = config.downloadDirectory + entry.filename
                if not os.path.exists(file_path):
                    logger.error("[PLAYBACK.START] Attempting to play a file that doesn't exist !")
                    self.dont_update_cursor_position = True
                    self.remove_entry(self.cursor)
                    await self.text_channel.send(f"Le Didjé a paumé le fichier de **{entry.title}**, on passe à la suivante du coup...")
                    self.__on_after_play()

            case EntryType.REMOTE:
                file_path: str = entry.remote_url

            case _:
                logger.error(f"[PLAYBACK.START] Attempting to play an unknown entry file that doesn't exist ! (GID:{self.guild_id})")
                self.dont_update_cursor_position = True
                self.remove_entry(self.cursor)
                await self.text_channel.send(f"J'ai trouvé une entrée bizarre et je sais pas quoi faire avec... bref, on passe à la suivante !")
                self.__on_after_play()
        
        
        
        

        #seek parameters
        before: str = ""
        if timestart > 0:
            before = f"-ss {timestart}"
        else:
            timestart = 0

        is_saturated = entry.is_saturated
        is_reversed = entry.is_reverse
        custom_options = ""
        if is_saturated or is_reversed:
            custom_options += f"-filter:a "
            contains_filters = False
            if is_saturated:
                custom_options += f"{"; " if contains_filters else ""}asoftclip=type=hard:threshold=0.01:output=8"
                contains_filters = True
            if is_reversed:
                custom_options += f"{"; " if contains_filters else ""}areverse"
                contains_filters = True

        player: discord.FFmpegOpusAudio = discord.FFmpegOpusAudio(
            file_path,
            before_options = before,
            options = f"-vn {custom_options}")
        
        self.stopped = False
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
        if self.next_entry_condition is AfterEntryPlaybackAction.SEEK:
            logger.debug(f"[QUEUE.AFTER_PLAY] on_after_play >> seek (GID:{self.guild_id})")
            return self.__play_seek()
        
        elif self.next_entry_condition is AfterEntryPlaybackAction.STOP:
            if not self.dont_update_cursor_position:
                self.__update_cursor_for_next_entry()

            logger.debug(f"[QUEUE.AFTER_PLAY] on_after_play >> stop (GID:{self.guild_id})")
            self.__stop_reset_play_status()
            return
        # elif self.next_entry_condition is NextEntryCondition.RESUME:
        #     pass
        
        logger.debug(f"[QUEUE.AFTER_PLAY] on_after_play >> next entry (GID:{self.guild_id})")
        self.__play_next()

        self.next_entry_condition = AfterEntryPlaybackAction.DEFAULT
        self.seek_time = -1
        self.dont_update_cursor_position = False
        pass



    def __update_cursor_for_next_entry(self):
        if self.repeat_mode == RepeatMode.NONE:
            self.cursor = self.cursor + 1
        elif self.repeat_mode == RepeatMode.ENTRY:
            pass
        elif self.repeat_mode == RepeatMode.QUEUE:
            if self.cursor == self.size - 1:
                self.cursor = 0
            else:
                self.cursor = self.cursor + 1
        elif self.repeat_mode == RepeatMode.PLAYLIST:
            def gotostart():
                i = self.cursor-1
                while self.entries[i].playlist is not None and i >= 0:
                    if self.entries[i].playlist.id == current_entry.playlist.id:
                        i = i-1
                    else:
                        break
                self.cursor = i

            current_entry = self.entries[self.cursor]
            if current_entry.playlist.id is not None:
                if self.cursor < self.size-1:
                    if self.entries[self.cursor+1].playlist is not None:
                        if self.entries[self.cursor+1].playlist.id != current_entry.playlist.id:
                            gotostart()
                    else:
                        gotostart()
                elif self.cursor == self.size - 1:
                    gotostart()

            self.cursor = self.cursor + 1



    def __play_next(self):
        if not self.dont_update_cursor_position:
            self.__update_cursor_for_next_entry()
            

        # defaulting class variables for next uses
        self.seek_time = -1
        self.dont_update_cursor_position = False
        if not self.ended:
            coro = self.start_playback()
            fut = asyncio.run_coroutine_threadsafe(coro, self.__voice_client.loop)
            try:
                fut.result()
            except Exception:
                logger.critical(f"[ERROR] play_next(): a coroutine error occured (GID:{self.guild_id})\n\n{traceback.format_exc()}")
        else:
            logger.debug(f"[PLAYBACK.PLAY_NEXT] End of queue (GID:{self.guild_id})")
            self.__stop_reset_play_status()
            


    def __play_seek(self):
        if self.seek_time < 0:
            return self.__play_next()
        # setting variables
        starting_time:int = self.seek_time

        # defaulting class variables for next uses
        self.seek_time = -1

        if not self.ended:
            coro = self.start_playback(timestart = starting_time)
            fut = asyncio.run_coroutine_threadsafe(coro, self.__voice_client.loop)
            try:
                fut.result()
            except Exception:
                logger.critical(f"[ERROR] play_seek(): a coroutine error occured (GID:{self.guild_id})\n\n{traceback.format_exc()}")
        else:
            logger.debug(f"[PLAYBACK.PLAY_NEXT] Attempted seek at queue but it's at the end, ignoring... (GID:{self.guild_id})")
            self.__stop_reset_play_status()


    def __stop_reset_play_status(self):
        #restore to defaults
        self.stopped = True
        self.next_entry_condition = AfterEntryPlaybackAction.DEFAULT
        self.seek_time = -1
        self.dont_update_cursor_position = False
        logger.debug("[PLAYBACK.STOP] playback stopped, and setting status to stopped")


    async def add_entry(self, entry: Entry, position: int = None) -> int:
        
        if position is None or position == self.size:
            if not entry.is_ready:
                #TODO: implement queueing
                return -1
            self.entries.append(entry)
        else:
            if not entry.is_ready:
                return -1
            self.entries.insert(position, entry)

        self.size = self.size + 1
        if self.size == self.cursor + 1:
            await self.start_playback()

        return position or self.size-1

    def move_entry(self, frm: int, to: int):
        entry = self.entries[frm]
        self.entries.pop(frm)
        self.entries.insert(to, entry)

    def remove_entry(self, index: int):
        self.entries.pop(index)
        self.size = self.size - 1


    


    def get_index(self, entry: Entry) -> int:
        return self.entries.index(entry)

    def get_entry(self, index: int) -> Entry:
        return self.entries[index]
    

