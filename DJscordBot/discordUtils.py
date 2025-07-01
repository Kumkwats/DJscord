import time

import discord
from discord import WebhookMessage, ApplicationContext

from DJscordBot.Types.queue import Queue
from DJscordBot.Types.entry import Entry, EntryType
from DJscordBot.utils import time_format



class DiscordInteractionWrapper():
    def __init__(self, context: ApplicationContext, currentMessage: WebhookMessage = None):
        self.context: ApplicationContext = context
        self.guild_ID: int = context.guild.id
        self.author: discord.User = context.author
        self.__message: WebhookMessage = currentMessage
        self.__last_message: str = ""


    async def whisper_to_author(self, content: str, write_new_message: bool = False):
        if self.__message is None or write_new_message:
            self.__last_message = content
            self.__message = await self.context.respond(content, ephemeral = True)
        else:
            self.__last_message = content
            await self.__message.edit(self.__last_message)


    async def append_to_last_whisper(self, content_to_append: str, new_line = True, save_edit = True):
        if self.__message is None:
            self.__last_message = content_to_append
            self.__message = await self.context.respond(self.__last_message, ephemeral = True)
        else:
            if new_line:
                content_to_append = "\n" + content_to_append
            if save_edit:
                self.__last_message += content_to_append
                await self.__message.edit(self.__last_message)
            else:
                await self.__message.edit(self.__last_message + content_to_append)


    async def send_message_in_author_channel(self, string: str):
        await self.context.send(string)




class EmbedBuilder():
    progress_bar_size = 25

    @classmethod
    def build_embed(cls, entry:Entry, queue_data: Queue) -> discord.Embed:
        time_elapsed: float = queue_data.pausetime - queue_data.starttime if queue_data.is_paused() else time.time() - queue_data.starttime

        entry_index = queue_data.get_index(entry)

        progress_text = ""
        if queue_data.cursor == entry_index:
            if entry.type == EntryType.FILE and entry.duration > 0:
                progress_text = f"{cls.__create_progress_bar(time_elapsed, entry.duration, queue_data.is_paused())}\n\n"
            else:
                progress_text = f"Durée d'écoute : {time_format(time_elapsed)} {'[Lecture suspendue]' if queue_data.is_paused() else ''}\n\n"

        description: str = ""
        if entry.type == EntryType.FILE and entry.duration > 0:
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
    






    # @classmethod
    # def __build_embed_for_youtube(cls, entry:Old_Entry, queue_data: Queue) -> discord.Embed:
    #     entry_index = queue_data.get_index(entry)
        
    #     yt_video: youtube.YoutubeVideo = entry.youtube_video
        
    #     main_content = ""

    #     if queue_data.cursor == entry_index:
    #         pause: str = "[Paused]" if queue_data.is_paused() else ""
    #         current: float = queue_data.pausetime - queue_data.starttime if queue_data.is_paused() else time.time() - queue_data.starttime
            
    #         if not hasattr(yt_video, 'duration'): #Other Stream
    #             main_content += f"Durée d'écoute : {time_format(current)} {pause}\n\n"
    #         else: #File
    #             main_content += f"Progression : {time_format(current)}/{time_format(yt_video.duration)} ({int((current/yt_video.duration)*100)}%) {pause}\n"
                
    #             #Progress bar
    #             progress = (current/yt_video.duration)*cls.progress_bar_size
    #             main_content += "["
    #             for i in range(0, cls.progress_bar_size):
    #                 if int(progress) == i:
    #                     main_content += "●"
    #                 else:
    #                     main_content += "─"
    #             main_content += f"]\n\n"
                

    #     # if hasattr(yt_video, 'like_count') and hasattr(yt_video, 'view_count'):
    #     #     main_content += f"{(yt_video.view_count)} vues | {yt_video.like_count} likes\n"

    #     # if hasattr(yt_video, 'channel') and hasattr(yt_video, 'channel_url'):
    #     #     main_content += f"Chaîne : [{yt_video.channel}]({yt_video.channel_url})"
    #     #     if hasattr(yt_video, 'channel_follower_count'):
    #     #         main_content += f" ({yt_video.channel_follower_count} abonnés)"
    #     #     main_content += "\n-# source: Youtube"
    #     #     main_content += "\n\n"


        

    #     # if hasattr(yt_video, 'album'):
    #     #     main_content += f"Album : {yt_video.album}\n\n"
    #     # if hasattr(entry, 'playlist'):
    #     #     if entry.playlist is not None :
    #     #         main_content += f"Playlist : [{entry.playlist.title}]({entry.playlist.url})\n\n"
    #     # main_content += f"Position dans la queue : {entry_index}"

    #     embed = discord.Embed(
    #         title = entry.get_title_embed(),
    #         url = yt_video.url,
    #         description = main_content,
    #         color = 0x565493
    #     )
    #     embed.set_image(url=yt_video.thumbnail)
    #     return embed


    # @classmethod
    # def __build_embed_for_spotify(cls, entry:Old_Entry, queue_data: Queue) -> discord.Embed:
    #     entry_index = queue_data.get_index(entry)
        
    #     spt_track: spotify.SpotifyTrack = entry.spotify_track
    #     yt_video: youtube.YoutubeVideo = entry.youtube_video

    #     main_content = ""

        


    #     # Album
    #     main_content += f"{spt_track.album.album_type.capitalize()} : [{spt_track.album.name}]({spt_track.album.web_url})\n"
    #     # main_content += f"({spt_track.track_number}/{spt_track.album.total_tracks}) [Disque {spt_track.disc_number}]\n"

    #     # Artiste
    #     main_content += f"Artiste : [{spt_track.artists[0].name}]({spt_track.artists[0].web_url})\n"

    #     # Progress Bar
    #     if queue_data.cursor == entry_index:
    #         pause_info: str = "[Paused]" if queue_data.is_paused() else ""
    #         current_timestamp: float = queue_data.pausetime - queue_data.starttime if queue_data.is_paused() else time.time() - queue_data.starttime
            
    #         if not hasattr(yt_video, 'duration'): #Live streams
    #             main_content += f"Durée d'écoute : {time_format(current_timestamp)} {pause_info}\n\n"
    #         else: #File
    #             main_content += f"Progression : {time_format(current_timestamp)}/{time_format(yt_video.duration)} ({int((current_timestamp/yt_video.duration)*100)}%) {pause_info}\n"
                
    #             #Progress bar
    #             progress = (current_timestamp/yt_video.duration)*cls.progress_bar_size
    #             main_content += "["
    #             for i in range(0,cls.progress_bar_size):
    #                 if int(progress) == i:
    #                     main_content += "●"
    #                 else:
    #                     main_content += "─"
    #             main_content += f"]\n\n"

    #     # Autre
    #     main_content += f"- Popularité : {spt_track.popularity}\n"
    #     main_content += "-# source: Spotify\n"

    #     if hasattr(yt_video, 'like_count') and hasattr(yt_video, 'view_count'):
    #         main_content += f"- {(yt_video.view_count)} vues | {yt_video.like_count} likes\n"
    #         main_content += "-# source: Youtube\n"

    #     if hasattr(entry, 'playlist'):
    #         if entry.playlist is not None :
    #             main_content += f"\nPlaylist : [{entry.playlist.title}]({entry.playlist.url})\n"
    #     main_content += f"\nPosition dans la queue : {entry_index}"



    #     embed = discord.Embed(
    #         title = entry.spotify_track.name,
    #         url = spt_track.web_url,
    #         description = main_content,
    #         color = 0x565493
    #     )
    #     embed.set_image(url=spt_track.album.image)
    #     return embed



    # def __build_embed_for_other_streams(entry:Old_Entry, queue_data: Queue) -> discord.Embed:
    #     embed = discord.Embed(
    #         title = entry.get_title_embed(),
    #         url = entry.url,
    #         description = "",
    #         color = 0x565493
    #     )

    #     return embed