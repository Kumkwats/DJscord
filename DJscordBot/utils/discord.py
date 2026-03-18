import time

import discord
from discord import Interaction

from ..Types.queue import Queue
from ..Types.entry import Entry, EntryType
from .format import time_format



class InteractionWrapper():
    """
    Class to abstract the command context (or now called Interaction) and have shorthands for commonly accessed context properties
    """
    def __init__(self, context: Interaction):
        self.interaction: Interaction = context
        self.guild_id: int = context.guild.id
        self.guild: discord.Guild = context.guild
        self.author: discord.Member = context.user
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
        # await self.context.followup.edit_message(self.__message_id, content=content)
        await self.interaction.edit_original_response(content=content, embed=embed)

    





class EmbedBuilder():
    """
    Class to easily create Discord embeds to display in interaction responses.
    """

    progress_bar_size = 25

    @classmethod
    def build_entry_info_embed(cls, entry:Entry, queue_data: Queue) -> discord.Embed:
        time_elapsed: float = queue_data.pausetime - queue_data.starttime if queue_data.is_paused else time.time() - queue_data.starttime

        entry_index = queue_data.get_index(entry)

        progress_text = ""
        if queue_data.cursor == entry_index:
            if entry.type == EntryType.LOCAL_FILE and entry.duration > 0:
                progress_text = f"{cls.__create_progress_bar(time_elapsed, entry.duration, queue_data.is_paused)}\n\n"
            else:
                progress_text = f"Durée d'écoute : {time_format(time_elapsed)} {'[Lecture suspendue]' if queue_data.is_paused else ''}\n\n"

        description: str = ""
        if entry.type == EntryType.LOCAL_FILE and entry.duration > 0:
            description += f"{progress_text}{entry.description}\n\n"
            
            description += f"Position dans la liste de lecture : {entry_index}"
            if entry.playlist is not None:
                description += f"\n-# Playlist : [{entry.playlist.title}]({entry.playlist.web_url})"


            
        embed: discord.Embed = None

        embed = discord.Embed(
            title = entry.title,
            url = entry.web_url,
            description = description,
            color = 0x565493
        )

        if entry.image_link is not None:
            embed.set_image(url = entry.image_link)
        #embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text = "Demandé par %s" % entry.user.display_name, icon_url = entry.user.display_avatar.url)

        return embed


    @classmethod
    def __create_progress_bar(cls, time_elapsed: float, duration: float, paused: bool = False):
        raw_progress: float = time_elapsed/duration # progress between 0 and 1

        progress_text = f"Progression : {time_format(time_elapsed)}/{time_format(duration)} ({int(raw_progress*100)}%) {'[Lecture suspendue]' if paused else ''}"
        stepped_progress = raw_progress*cls.progress_bar_size
        progress_bar_str = "["
        for i in range(0, cls.progress_bar_size):
            if int(stepped_progress) == i:
                progress_bar_str += "●"
            else:
                progress_bar_str += "─"
        progress_bar_str += f"]"
        return f"{progress_text}\n{progress_bar_str}"
    
