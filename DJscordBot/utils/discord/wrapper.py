import asyncio

import discord
from discord import Interaction

from DJscordBot.utils.discord.message import InteractionMessageContent

class InteractionWrapper():
    """
    Class to abstract the command context (or now called Interaction) and have shorthands for commonly accessed context properties
    """
    def __init__(self, context: Interaction):
        self.interaction: Interaction = context
        self.guild_id: int = context.guild.id
        self.guild: discord.Guild = context.guild
        self.author: discord.Member = context.user
        self.message: InteractionMessageContent = None
        self._message_id: int = None
        self._last_message_content: str = ""

    @property
    def voice_client(self) -> discord.VoiceClient | None:
        return self.interaction.guild.voice_client


    async def think(self, ephemeral = False):
        if self._message_id is None:
            callback_response: discord.InteractionCallbackResponse = await self.interaction.response.defer(ephemeral=ephemeral)
            self._message_id = callback_response.message_id

    async def send_message_in_author_channel(self, string: str):
        await self.interaction.channel.send(string)



    async def respond(self, content:str, ephemeral: bool = False):
        if self._message_id is None:
            self._last_message_content = content
            await self.__init_response(content, ephemeral=ephemeral)
        else:
            self._last_message_content = content
            await self.__edit_message(self._last_message_content)

    async def send_embed(self, embed: discord.Embed, ephemeral: bool = False):
        if self._message_id is None:
            await self.__init_response(None, embed=embed, ephemeral=ephemeral)
        else:
            await self.__edit_message(None, embed=embed)


    
    async def whisper_to_author(self, content: str):
        await self.respond(content, ephemeral=True)


    async def append_to_last_whisper(self, content_to_append: str, new_line = True, save_edit = True):
        if self._message_id is None:
            self._last_message_content = content_to_append
            await self.__init_response(self._last_message_content, ephemeral = True)
        else:
            if new_line:
                content_to_append = "\n" + content_to_append
            if save_edit:
                self._last_message_content += content_to_append
                await self.__edit_message(self._last_message_content)
            else:
                await self.__edit_message(self._last_message_content + content_to_append)


    async def __init_response(self, content: str, embed: discord.Embed = None, ephemeral: bool = False):
        callback_response = await self.interaction.response.send_message(content, embed=embed, ephemeral = ephemeral)
        self._message_id = callback_response.message_id

    async def __edit_message(self, content: str, embed: discord.Embed = None):
        await self.interaction.edit_original_response(content=content, embed=embed)
