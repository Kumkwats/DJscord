import discord

from ...Types.entry import Entry
from ...Types.queue import Queue

from ..format import time_format


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
            if entry.duration > 0:
                progress_text = f"{cls.__create_progress_bar(time_elapsed, entry.duration, queue_data.is_paused, yt_video_url=entry.yt_video_url)}\n\n"
            else:
                progress_text = f"Durée d'écoute : {time_format(time_elapsed)} {'[Lecture suspendue]' if queue_data.is_paused else ''}\n\n"

        description: str = ""
        if entry.type == EntryType.LOCAL_FILE and entry.duration > 0:
            description += f"{progress_text}\n{entry.description}\n\n"
            
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
    def __create_progress_bar(cls, time_elapsed: float, duration: float, paused: bool = False, *, yt_video_url: str = None):
        raw_progress: float = time_elapsed/duration # progress between 0 and 1

        if yt_video_url is not None or yt_video_url != "":
            progress_text = f"Progression : [{time_format(time_elapsed)}]({yt_video_url}&t={int(time_elapsed)}s)/{time_format(duration)}"
        else:
            progress_text = f"Progression : {time_format(time_elapsed)}/{time_format(duration)}"
        progress_text += f" ({int(raw_progress*100)}%) {'[Lecture suspendue]' if paused else ''}"

        stepped_progress = raw_progress*cls.progress_bar_size
        progress_bar_str = "["
        for i in range(0, cls.progress_bar_size):
            if int(stepped_progress) == i:
                progress_bar_str += "●"
            else:
                progress_bar_str += "─"
        progress_bar_str += f"]"
        return f"{progress_text}\n{progress_bar_str}"
    
