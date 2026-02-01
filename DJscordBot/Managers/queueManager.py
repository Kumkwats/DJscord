import os
import asyncio

import discord


from ..config import config
from ..client import DJscordClient
from ..Types.queue import Queue

from ..logging.utils import get_logger
logger = get_logger("djscordbot.manager.queue")

class QueueManager():
    __queues: 'dict[int, Queue]' = {}

    @classmethod
    async def create_queue(self, guild_id: int, voice_client: discord.VoiceClient, text_channel: discord.TextChannel, bot_user: DJscordClient) -> Queue:
        self.__queues[guild_id] = Queue(guild_id, voice_client, text_channel)
        logger.info(f"[CREATE] Created queue for guild ({guild_id})")
        await self.__queues[guild_id].boot(bot_user)
        return self.__queues[guild_id]

    @classmethod
    def get_queue(self, guild_id: int) -> Queue | None:
        if not self.is_guild_active(guild_id):
            return None
        return self.__queues[guild_id]

    @classmethod
    def get_every_guild_id(self):
        return self.__queues.keys()
    
    @classmethod
    def is_guild_active(self, guild_id):
        return guild_id in self.__queues


    # @classmethod
    # def create_or_get_queue(cls, guild_id: int, voice_client: discord.VoiceClient, text_channel: discord.TextChannel) -> Queue:
    #     queue = cls.get_queue(guild_id)
    #     if queue is None:
    #         return cls.create_queue(guild_id, voice_client, text_channel)
    #     return queue


    @classmethod
    async def remove_queue(cls, guild_id: int) -> bool:
        if guild_id not in cls.__queues:
            logger.error(f"[REMOVE] guild({guild_id}) already removed")
            return
        if not cls.__queues[guild_id].has_voice_client:
            cls.__queues.pop(guild_id)
            logger.debug(f"[REMOVE] Removed guild({guild_id}), had no VoiceClient")
            return

        if not cls.__queues[guild_id].is_connected:
            cls.__queues.pop(guild_id)
            logger.debug(f"[REMOVE] Removed guild({guild_id}), had a VoiceClient but wasn't connected")
            return
        # Stop play if need
        if cls.__queues[guild_id].is_playing:
            await cls.__queues[guild_id].stop()
            logger.debug(f"[REMOVE] VoiceClient stoped in guild({guild_id}) ")
        await asyncio.sleep(0.6)
        
        # Disconnect
        await cls.__queues[guild_id].disconnect_and_cleanup()
        logger.debug(f"[REMOVE] Disconnected in Guild({guild_id})")

        await asyncio.sleep(0.2)
        for entry in cls.__queues[guild_id].entries:
            if entry.filename in os.listdir(config.downloadDirectory): #TODO implement waiting for process to stop using the file before trying to remove it
                try:
                    os.remove(config.downloadDirectory + entry.filename) #If running on Windows, the file currently playing is not erased
                except PermissionError :
                    logger.error(f"[REMOVE.FILE.EXCEPTION] PermissionError/Not allowed to remove file ({config.downloadDirectory + entry.filename})")
        
        cls.__queues.pop(guild_id)
        logger.info(f"[REMOVE] Removed guild({guild_id})")
