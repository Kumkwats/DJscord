import os
import asyncio
import time

import discord
from discord.ext import tasks


from ..config import config
from ..client import DJscordClient
from ..utils.discord import InteractionWrapper, EmbedBuilder
from ..Types.entry import Entry, EntryPlaylist
from ..Types.queue import Queue
from ..Types.enums import AfterEntryPlaybackAction, RepeatMode
from ..Managers.queueManager import QueueManager
from ..utils.format import time_format
from ..utils.io import pick_sound_file

from .processors.cmd_music_play import PlayCmdProcessor

from ..logging.utils import get_logger
logger = get_logger("djscordbot.commands.music")


VOICE_ACTIVITY_CHECK_DELTA = 10 #number of seconds between every AFK check

# Queues: 'dict[int, Queue]' = {}




class Music():
    def __init__(self, bot: DJscordClient):
        self.bot = bot
        if config.leave_afk_enabled:
            #self.music_timeout.start()
            pass

    
#region To sort
    @staticmethod
    def author_voice_is_connected(interac_wrapper: InteractionWrapper) -> bool:
        if interac_wrapper.author.voice is None: # Not connected
            logger.error(f"[CONNECT] no author_voice, cannot connect (GID:{interac_wrapper.guild.id})")
            return False
        return True



#endregion







#region CMD
    async def cmd_play(self, interac_wrapper: InteractionWrapper, cmd_query: str):
        await interac_wrapper.think(ephemeral=True)
        
        guild_id = interac_wrapper.guild.id

        if not self.author_voice_is_connected(interac_wrapper): # Not connected
            logger.error(f"[AUTHOR_VOICE] no author_voice, cannot connect (GID:{guild_id})")
            return await interac_wrapper.respond(
                "Vous devez être connecté à un salon vocal pour pouvoir ajouter de la musique",
                ephemeral=True)

        author_voice_channel: discord.VoiceChannel = interac_wrapper.author.voice.channel
        
        #New Guild
        queue: Queue = QueueManager.get_queue(guild_id)
        if queue is None:
            logger.debug(f"[VOICE.CONNECT.NEW] New queue, attempting connection... (GID:{guild_id})")
            new_voice_client: discord.VoiceClient = None
            err_message: str = ""
            (new_voice_client, err_message) = self.__attempt_connection(interac_wrapper.author.voice.channel, guild_id)
            
            if new_voice_client is None:
                logger.error(f"[VOICE.CONNECT.NEW] voice channel is None (GID:{guild_id})")
                return await interac_wrapper.whisper_to_author(err_message)

            queue = await QueueManager.create_queue(guild_id, new_voice_client, interac_wrapper.interaction.channel, self.bot)

        #Existing queue checks
        else:
            current_queue_voice_channel: discord.VoiceChannel = queue.voice_channel
            if not queue.is_connected:
                logger.info(f"[VOICE.STATUS] voice client apparently not connected, attempting reconnection... (GID:{guild_id})")
                (success, err_message) = self.__attempt_recovering_unexpected_no_voice_channel(author_voice_channel)
                if not success:
                    await interac_wrapper.whisper_to_author(err_message)
                    return await QueueManager.remove_queue(guild_id)
            else:
                if author_voice_channel != current_queue_voice_channel:
                    if not self.__attempt_move(queue, author_voice_channel):
                        return await interac_wrapper.whisper_to_author("Une erreur est survenue lors du déplacement du bot")

        play_cmd_transaction: PlayCmdProcessor = PlayCmdProcessor(interac_wrapper, self.bot)
        return await play_cmd_transaction.process_query(cmd_query)


    async def __attempt_connection(self, author_voice_channel: discord.VoiceChannel, guild_id: int) -> tuple[discord.VoiceClient, str]:
        voice_client: discord.VoiceClient = None
        try:
            voice_client = await author_voice_channel.connect(timeout=60)
        except asyncio.TimeoutError as toErr:
            logger.error(f"[VOICE.CONNECT.TIMEOUT] connect timed out... (GID:{guild_id})\n\tException: '{toErr}'")
            return (None, "Je n'ai pas eu de réponse de Discord pour me connecter... veuillez réessayer ultérieurement")
        except discord.ClientException as cEx:
            logger.error(f"[VOICE.CONNECT.CLIENT] unable to connect to VC because it is already connected to a voice client... (GID:{guild_id})")
            return (None, "Une erreur est survenue lors de la connection au channel vocal")
        return (voice_client, "")
    
    async def __attempt_move(self, queue: Queue, author_voice_channel: discord.VoiceChannel) -> bool:
        try:
            await queue.move(author_voice_channel)
            logger.info(f"[VOICE.MOVE] moved to new channel : {author_voice_channel} (GID:{queue.guild_id})")
        except asyncio.TimeoutError as toErr:
            logger.error(f"[VOICE.MOVE.TIMEOUT] connect timed out... (GID:{queue.guild_id})\n\tException: '{toErr}'")
            return False
            # return await interac_wrapper.whisper_to_author("Discord ne m'a pas donné de réponse... veuillez réessayer ultérieurement")
        return True

    async def __attempt_recovering_unexpected_no_voice_channel(self, queue: Queue, author_voice_channel: discord.VoiceChannel) -> tuple[discord.VoiceClient, str]:
        try:
            await queue.connect(author_voice_channel)
        except asyncio.TimeoutError as toErr:
            logger.error(f"[VOICE.RECONNECT.TIMEOUT] connect timed out... (GID:{queue.guild_id})\n\tException: '{toErr}'")
            return (False, "Discord ne m'a pas donné de réponse... veuillez réessayer ultérieurement")
        except discord.ClientException as cEx:
            logger.error(f"[VOICE.RECONNECT.CLIENT] unable to connect to VC because it is already connected to a voice client... attempting move (GID:{guild_id})'")
            try:
                queue.move(author_voice_channel)
            except asyncio.TimeoutError as toErr:
                logger.error(f"[VOICE.MOVE.TIMEOUT] move timed out... (GID:{queue.guild_id})\n\tException: '{toErr}'")
                return (False, "Discord ne m'a pas donné de réponse... veuillez réessayer ultérieurement")

        if not queue.is_connected:
            logger.error(f"[VOICE.RECONNECT] voice client unable to reconnect, aborting and removing guild (GID:{queue.guild_id})")
            return (False, "Une erreur est survenue, je suis perdu... veuillez réessayer ultérieurement")
        logger.info(f"[VOICE.RECONNECT] voice client sucessfully reconnected (GID:{queue.guild_id})")
        return (True, "")


#region player cmds
    async def seek(self, interac_wrapper: InteractionWrapper, timeCode: str = None):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)

        if queue is None or queue.stopped:
            return await interac_wrapper.whisper_to_author("Pas de lecture en cours")

        currentEntry = queue.entries[queue.cursor]
        if currentEntry.duration <= 0:
            return await interac_wrapper.whisper_to_author("Ce morceau n'est pas seekable")

        #Decoding timeCode
        try:
            time = list(map(int, timeCode.split(":")))[::-1]
        except:
            return await interac_wrapper.whisper_to_author("Quelque chose ne va pas dans la syntaxe (doit être hhhh:mm:ss ou mmmm:ss ou bien ssss)")
        (secs, mins, hrs) = (0,0,0)
        secs = time[0]
        if len(time) > 1:
            if 0 <= secs < 60:
                mins = time[1]
            else: #TODO specify error
                return await interac_wrapper.whisper_to_author("Le temps n'est pas conforme")
            if len(time) > 2:
                if  0 <= mins < 60:
                    hrs = time[2]
                else:
                    return await interac_wrapper.whisper_to_author("Le temps n'est pas conforme")
                if hrs < 0:
                    return await interac_wrapper.whisper_to_author("Le temps n'est pas conforme")
        desiredStart = secs + 60*mins + 60*60*hrs
        
        if 0 <= desiredStart < currentEntry.duration -1:
            queue.next_entry_condition = AfterEntryPlaybackAction.SEEK
            queue.seek_time = desiredStart
            queue.stop()
            return await interac_wrapper.respond(f"Utilisation de Seek:tm: !") #TODO better response
        else:
            return await interac_wrapper.whisper_to_author(f"La vidéo sera déjà finie à {time_format(desiredStart)}...")



    async def pause(self, interac_wrapper: InteractionWrapper):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)
        
        if queue is not None:
            if queue.is_playing:
                queue.pause()
                queue.pausetime = time.time()
                logger.info(f"[PAUSE] paused player (GID:{queue.guild_id})")
                return await interac_wrapper.respond("Lecture mise en pause")
            else:
                return await interac_wrapper.whisper_to_author("Lecture déjà en pause !")
        else:
            logger.error(f"[PAUSE] pause() called but not in the registered guilds (GID:{queue.guild_id})")
            return await interac_wrapper.whisper_to_author("Selon les informations que je possède, il n'y a aucune lecture en cours sur ce serveur")


    async def resume(self, interac_wrapper: InteractionWrapper):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)
        if queue is not None:
            if queue.is_paused:
                queue.resume()
                queue.starttime = time.time() - (queue.pausetime - queue.starttime) # Setting starttime to the correct time to ensure that the time elapsed on the entry is correct when resuming
                queue.pausetime = 0
                logger.info(f"[RESUME] resumed player (GID:{queue.guild_id})")
                return await interac_wrapper.respond("Reprise de la lecture")
            else:
                return await interac_wrapper.whisper_to_author("On est déjà en lecture !")
        else:
            logger.error(f"[RESUME] resume() called but not in the registered guilds (GID:{queue.guild_id})")
            return await interac_wrapper.whisper_to_author("Selon les informations que je possède, il n'y a aucune lecture en cours sur ce serveur")

    
    async def stop(self, interac_wrapper: InteractionWrapper):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)
        
        if queue.has_voice_client:
            if queue.is_playing or queue.is_paused:
                if interac_wrapper.author.voice is None or interac_wrapper.author.voice.channel != queue.voice_channel:
                    return await interac_wrapper.whisper_to_author("Je suis en train de jouer de la musique là, viens me le dire en face !")
                queue.next_entry_condition = AfterEntryPlaybackAction.STOP
                queue.dont_update_cursor_position = True
                queue.stop()
                logger.info(f"[STOP] stopped listening (GID:{queue.guild_id})")
                return await interac_wrapper.respond("Ok j'arrête de lire la musique :(")
        else:
            logger.error(f"[STOP] stop() called but not in the registered guilds (GID:{queue.guild_id})")
            return await interac_wrapper.whisper_to_author("Selon les informations que je possède, je suis pas connecté sur ce serveur.")

#endregion





#region entry info
    async def info(self, interac_wrapper: InteractionWrapper, index: int):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)

        if queue is None:
            return await interac_wrapper.whisper_to_author("Aucune liste de lecture")
        
        if index >= queue.size and index < 0:
            return await interac_wrapper.whisper_to_author('L\'index %d n\'existe pas' % (index))
        
        entry = queue.entries[index]

        embed: discord.Embed = EmbedBuilder.build_entry_info_embed(entry, queue)
        if queue.cursor == index:
            play_status = " ❚❚" if queue.is_paused else " ▶"
            name = play_status + "\t" + (" En pause" if queue.is_paused else " En cours de lecture")
        else:
            name = "Informations piste"
        embed.set_author(name = name, icon_url = self.bot.user.display_avatar.url)
        return await interac_wrapper.send_embed(embed=embed)



    async def now_playing(self, interac_wrapper: InteractionWrapper):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)
        if queue is None or queue.ended or queue.stopped:
            return await interac_wrapper.whisper_to_author('Rien en lecture')
        else:
            await self.info(interac_wrapper, queue.cursor)

#endregion





#region queue cmds
    async def print_queue(self, interac_wrapper: InteractionWrapper, page:int = None):

        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)
        if queue is None:
            return await interac_wrapper.whisper_to_author('Aucune liste de lecture sur ce serveur')


        total_duration = 0
        total_size = 0
        queue_list = ""
        

        #TODO add this to the config file
        print_size = 20
        print_min, print_max = 0, queue.size #default values
        
        if page is None:
            print_min = max(queue.cursor - print_size // 2, 0)
            print_max = min(print_min + print_size, queue.size)
        else:
            if (page - 1) * print_size > queue.size or page < 1:
                return await interac_wrapper.whisper_to_author('Index de page invalide')
            
            print_min = (page - 1)*print_size
            print_max = min(print_min + print_size, queue.size)
        
        if print_min == 0:
            queue_list += "==== Début de la file\n"
        else:
            queue_list += "⠀⠀⠀⠀…\n"
            

        current_playlist: EntryPlaylist = None
        for index in range(print_min, print_max):
            entry: Entry = queue.entries[index]
            #Line variables
            tab = ""

            indicator = "\u2003\u2003"
            if queue.cursor == index:
                if queue.repeat_mode == RepeatMode.ENTRY:
                    indicator = "\u2002\u2006⟳\u2002"
                else:
                    indicator = "\u2003→\u2004"

            title: str = entry.title
                
            duration: int = 0
            if hasattr(entry, 'duration'): duration = entry.duration

            total_duration += duration

            file_size_str = ""
            if hasattr(entry, 'size'): file_size_str = entry.size/1000000


            if entry.playlist is not None:
                tab = "⠀⠀⠀⠀"
                if current_playlist is None or current_playlist.id != entry.playlist.id:
                    current_playlist = entry.playlist
                    if queue.repeat_mode == RepeatMode.PLAYLIST:
                        queue_list += "⟳ ⠀"
                    else:
                        queue_list += "⠀⠀ "
                    queue_list += f" Playlist : {current_playlist.title}\n"
                
            
            

            queue_list += f"{tab}{indicator}{index}: {title} - {time_format(duration)}\n"

            
            # totalSize += entry.fileSize


        if print_max == queue.size:
            queue_list += "==== Fin de la file"
        else:
            queue_list += "⠀⠀⠀⠀…"
        
        repeat_text = {
            RepeatMode.NONE: "Aucun",
            RepeatMode.ENTRY: "Musique en cours",
            RepeatMode.QUEUE: "Liste de lecture",
            RepeatMode.PLAYLIST: "Playlist"
        }

        embed = discord.Embed(
            description=queue_list,
            color=0x565493
        )
        # | Taille totale : %.2fMo .... , totalSize/1000000
        footerText = f"Nombre d'entrées : {queue.size} | Mode de répétition : {repeat_text[queue.repeat_mode]}\nDurée totale : {time_format(total_duration)} "
        if page is not None:
            footerText += f"\nPage {page}/{((queue.size - 1) // print_size) + 1}"

        if self.bot.user.avatar is None:
            embed.set_author(name = "Liste de lecture")
        else:    
            embed.set_author(name = "Liste de lecture", icon_url = self.bot.user.avatar.url)

        embed.set_footer(text = footerText)

        return await interac_wrapper.send_embed(embed=embed)
    

    
    async def move(self, interac_wrapper: InteractionWrapper, frm: int, to: int):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)
        if queue is None:
            return await interac_wrapper.whisper_to_author("Aucune liste de lecture")

        if frm == to:
            return await interac_wrapper.whisper_to_author('La destination ne peut pas être égale à la source')

        if frm < queue.size and frm >= 0 and to < queue.size and to >= 0:
            moved_entry_title = queue.get_entry(frm).title
            queue.move_entry(frm, to)

            #global announce
            #await interac_wrapper.respond(f"La piste n°{frm} a été déplacé à la position {to}")
            #user response
            await interac_wrapper.whisper_to_author(f"{moved_entry_title} a été déplacé de {frm} vers {to}")
            return
        else:
            return await interac_wrapper.whisper_to_author("Une des deux positions est invalide")

    #TODO Range Stops even if before or after cursor
    async def remove(self, interac_wrapper: InteractionWrapper, idx1: int, idx2: int = None):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)
        
        if queue is None:
            return await interac_wrapper.whisper_to_author("Aucune liste de lecture")
                    
        if idx1 >= queue.size or idx1 < 0:
            return await interac_wrapper.whisper_to_author(f"L'index 1 ({idx1}) n'existe pas dans la queue")
        
        if idx2 is None: # remove one entry
            entry = queue.get_entry(idx1)
            # stop playback if current entry is being removed
            queue.remove_entry(idx1)
            if idx1 == queue.cursor:
                queue.stop()
            # move cursor if removed item was before
            if idx1 <= queue.cursor:
                queue.cursor -= 1
            # remove associated file
            if entry.filename in os.listdir(config.downloadDirectory):
                os.remove(config.downloadDirectory + entry.filename)
            logger.info(f"[REMOVE] Entry number {idx1} has been removed (GID:{queue.guild_id})")
            return await interac_wrapper.respond(f"{entry.title} a bien été supprimé")
        
        else: # remove multiple entries
            oldSize = queue.size
            # index checks
            if idx2 >= oldSize or idx2 < 0:
                return await interac_wrapper.whisper_to_author(f"L'index 2 ({idx2}) n'existe pas dans la liste de lecture")
            if idx1 > idx2:
                return await interac_wrapper.whisper_to_author("Attention à l'ordre des index !")
            
            if idx1 <= queue.cursor <= idx2:
                queue.dont_update_cursor_position = True
                queue.next_entry_condition = AfterEntryPlaybackAction.STOP
                queue.stop()

            for i in range(idx2 - idx1 + 1):
                entry = queue.get_entry(idx1)
                queue.remove_entry(idx1)
                if idx1 <= queue.cursor:
                    queue.cursor -= 1
                if entry.filename in os.listdir(config.downloadDirectory):
                    os.remove(config.downloadDirectory + entry.filename)

            
            logger.info(f"[REMOVE] Entries in range ({idx1} - {idx2}) have been removed (GID:{queue.guild_id})")
            return await interac_wrapper.respond(f"Les entrées commençant à {idx1} jusqu'à {('la fin de la liste' if idx2 == oldSize else str(idx2))} ont bien été supprimés")
        


    
    async def skip(self, interac_wrapper: InteractionWrapper):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)

        if queue is not None:
            if queue.cursor < queue.size:
                queue.next_entry_condition = AfterEntryPlaybackAction.SKIP
                queue.dont_update_cursor_position = True
                queue.cursor = queue.cursor + 1
                queue.stop()
                return await interac_wrapper.respond("Passage à la musique suivante")
            else:
                return await interac_wrapper.whisper_to_author('Nous sommes à la fin de la liste de lecture')
        else:
            return await interac_wrapper.whisper_to_author('Aucune liste de lecture sur ce serveur')

#endregion





    async def leave(self, interac_wrapper: InteractionWrapper):
        guild_id = interac_wrapper.guild.id

        guild_queue: Queue = QueueManager.get_queue(guild_id)

        if guild_queue is None or not guild_queue.has_voice_client:
            voice_client: discord.VoiceClient = self.__get_voice_client_from_guild(guild_id)
            if voice_client is not None:
                await voice_client.disconnect()
                voice_client.cleanup()
                logger.warning(f"[LEAVE] Disconnected lone voice_client (GID:{guild_id})")
                return await interac_wrapper.respond('Ok bye!')
            else:
                logger.error(f"[LEAVE] leave() called but not in the registered guilds (GID:{guild_id})")
                return await interac_wrapper.whisper_to_author("Selon les informations que je possède, je suis pas connecté sur ce serveur.")


        if guild_queue.is_playing and (interac_wrapper.author.voice is None or interac_wrapper.author.voice.channel != guild_queue.voice_channel):
            return await interac_wrapper.whisper_to_author("Je suis en train de jouer de la musique là, viens me le dire en face !")
        guild_queue.next_entry_condition = AfterEntryPlaybackAction.STOP
        guild_queue.stop()
        await guild_queue.disconnect()
        logger.info(f"[MUSIC.LEAVE] Disconnected voice_client (GID:{guild_id})")
        await asyncio.sleep(0.2)
        for entry in guild_queue.entries:
            if entry.filename in os.listdir(config.downloadDirectory):
                try:
                    os.remove(config.downloadDirectory + entry.filename) # If running on Windows), the file currently playing will not be erased
                except:
                    logger.error(f"[LEAVE.CLEANUP] error while removing file \"{entry.filename}\" (GID:{guild_id})")
                    continue
        await QueueManager.remove_queue(guild_id)
        return await interac_wrapper.respond('Ok bye!')


    #TODO ERROR command not found
    async def repeat(self, interac_wrapper: InteractionWrapper, mode: RepeatMode):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)

        if queue is None:
            return await interac_wrapper.whisper_to_author("Aucune liste de lecture")

        repeat_text = {
            RepeatMode.NO_REPEAT: "Pas de répétition",
            RepeatMode.ENTRY: "Musique en cours",
            RepeatMode.ALL: "Liste de lecture entière",
            RepeatMode.PLAYLIST: "Playlist"
        }

        if mode is not None:
            match mode:
                case 'none':
                    queue.repeat_mode = RepeatMode.NO_REPEAT
                case 'entry':
                    queue.repeat_mode = RepeatMode.ENTRY
                case 'playlist':
                    queue.repeat_mode = RepeatMode.PLAYLIST
                case 'all':
                    queue.repeat_mode = RepeatMode.ALL
                case _:
                    return await interac_wrapper.whisper_to_author(f":warning: `{mode}` n'est pas un mode de répétition existant")
            return await interac_wrapper.respond(f"Le mode de répétition à été changé sur `{repeat_text[queue.repeat_mode]}`")
        else:
            repeat_modes = [RepeatMode.NO_REPEAT, RepeatMode.ENTRY, RepeatMode.PLAYLIST, RepeatMode.ALL]
            old_mode = queue.repeat_mode
            new_mode = repeat_modes[(repeat_modes.index(old_mode) + 1) % len(repeat_modes)]
            queue.repeat_mode = new_mode
            return await interac_wrapper.respond(f"Le mode de répétition à été changé sur `{new_mode}`")

    
    async def goto(self, interac_wrapper: InteractionWrapper, index: int):
        queue: Queue = QueueManager.get_queue(interac_wrapper.guild.id)

        if queue is None:
            return await interac_wrapper.whisper_to_author("Aucune liste de lecture")
        
        if not queue.has_voice_client:
            logger.error("[GOTO] guild(%d) has no VoiceClient")
            #TODO Handle queue tests (maybe in a separate method)
            return await interac_wrapper.whisper_to_author(":warning: Une erreur est survenue lors de la commande")

        if index < queue.size and index >= 0:
            queue.cursor = index
            if queue.is_playing or queue.is_paused:
                queue.dont_update_cursor_position = True
                queue.stop()
            else:
                await queue.start_playback()
            return  await interac_wrapper.respond(f"Direction la musique n°{index}")
        else:
            return await interac_wrapper.whisper_to_author(f"L'index `{index}` n'est pas valide")



    

    def __get_voice_client_from_guild(self, guild_id: int) -> discord.VoiceClient | None:
        voice_client_list: list[discord.VoiceClient] = self.bot.voice_clients
        for voice_client in voice_client_list:
            if voice_client.guild.id == guild_id:
                return voice_client
        return None

#endregion





#region Loop Tasks
#TODO broken
    #afk loop
    @tasks.loop(seconds=VOICE_ACTIVITY_CHECK_DELTA)
    async def music_timeout(self):
        guilds_to_disconnect = []
        
        for guild_id in QueueManager.get_every_guild_id():
            guild_queue = QueueManager.get_queue(guild_id)
            if guild_queue.__voice_client is None:
                guilds_to_disconnect.append(guild_id)
                logger.info(f"[TIMEOUT] Guild ({guild_queue}) has no voice_client, will be removed")
            else:
                if guild_queue.is_playing:
                    guild_queue.update_last_voice_activity()
                else:
                    if time.time() - guild_queue.last_voice_activity_time >= config.leave_afk_time*60:
                        guilds_to_disconnect.append(guild_id)
                        logger.info(f"[TIMEOUT] Guild ({guild_id}) has been inactive for too long, will be removed (AFK time = {time.time() - guild_queue.last_voice_activity_time} seconds)")
                        
        
        if len(guilds_to_disconnect) > 0:
            for guild_id in guilds_to_disconnect:
                guild_to_disconnect = QueueManager.get_queue(guild_id)
                check, file = pick_sound_file("leave")
                if check:
                    if file != "":
                        if guild_to_disconnect.__voice_client is not None:
                            player = discord.FFmpegPCMAudio(file, options="-vn")
                            guild_to_disconnect.__voice_client.play(player, after=lambda e: guild_to_disconnect.__voice_client.loop.create_task(QueueManager.remove_queue(guild_id)))
                    else:
                        logger.debug("[TIMEOUT] no leaving sounds found")
                else:
                    logger.debug("[TIMEOUT] sounds folder not found")
                    
                while guild_to_disconnect.__voice_client.is_playing():
                    await asyncio.sleep(0.1)

                await guild_to_disconnect.disconnect()
                await QueueManager.remove_queue(guild_id)
                logger.info(f"[TIMEOUT]Disconnected for inactivity GID({guild_queue})")

#endregion
