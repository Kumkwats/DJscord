import os
import asyncio
import time

import discord
from discord.ext import tasks, commands


from DJscordBot.Managers.queueManager import QueueManager
from DJscordBot.discordUtils import DiscordInteractionWrapper, EmbedBuilder
from DJscordBot.Types.queue import Queue, NextEntryCondition, RepeatMode
from DJscordBot.Types.entry import Entry
from DJscordBot.utils import time_format, pick_sound_file
from DJscordBot.config import config

from DJscordBot.Future.cmdPlayTransaction import MusicPlayCommandTransaction


VOICE_ACTIVITY_CHECK_DELTA = 10 #number of seconds between every AFK check

# Queues: 'dict[int, Queue]' = {}




class Music():
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        if config.afkLeaveActive:
            #self.music_timeout.start()
            pass

    
#region To sort
    @staticmethod
    def author_voice_is_connected(ctx: discord.ApplicationContext) -> bool:
        if ctx.author.voice is None: # Not connected
            print(f"[CONNECT.ERROR] no author_voice, cannot connect (GID:{ctx.guild.id})")
            return False
        return True

    # async def searchAndPlay(self, ctx: discord.ApplicationContext, search_query: str):
    #     print(f"[QUERY.PROCESS.SEARCH] begin youtube search with query: \"{search_query}\" (GID:{discordUserResponse.guildID})")
    #     result = await self.youtube_process_search(cmd_query, discordUserResponse)
    #     try:
    #         data = result
    #         print(f"[YOUTUBE.SUCCESS] found link \"{(result['webpage_url'])}\" | (GID:{discordUserResponse.guildID})")
    #     except Exception:
    #         print(f"[YOUTUBE.ERROR] link check failed\n\n{traceback.format_exc()} | (GID:{discordUserResponse.guildID})")
    #         return await discordUserResponse.WriteUserResponse('Une erreur est survenue lors de la vérification du lien')
    #     return await self.youtube_process_final(result)

#endregion







#region CMD
    async def cmd_play(self, ctx: discord.ApplicationContext, cmd_query: str):
        await ctx.defer(ephemeral=True)
        
        guild_id = ctx.guild.id

        if not self.author_voice_is_connected(ctx): # Not connected
            print(f"[CONNECT.ERROR] no author_voice, cannot connect (GID:{guild_id})")
            return await ctx.respond(
                "Vous devez être connecté à un salon vocal pour pouvoir ajouter de la musique",
                ephemeral=True)

        
        discordUserResponse: DiscordInteractionWrapper = DiscordInteractionWrapper(ctx)

        
        #New Guild
        queue: Queue = QueueManager.get_queue(guild_id)
        if queue is None:
            new_voice_client: discord.VoiceClient = None
            print(f"[QUEUE.NEW.CONNECT.VC] New queue, attempting connection... (GID:{guild_id})")
            try:
                new_voice_client = await ctx.author.voice.channel.connect(timeout=60)
            except discord.ClientException as cEx:
                print(f"[CONNECT.VC.EXCEPTION] unable to connect to VC:\n{cEx}")
                return await discordUserResponse.whisper_to_author("Une erreur est survenue lors de la connection au channel vocal")

            if new_voice_client is None:
                print(f"[CONNECT.VC.EXCEPTION] VC is None")

            queue = QueueManager.create_queue(guild_id, new_voice_client, ctx.channel)
            boot_entry = self.__create_boot_entry()
            if boot_entry is not None:
                queue.add_entry(boot_entry)

            # queue = await self.__initialize_queue(ctx)

        #Existing queue checks
        else:
            print(f"[QUEUE] existing queue, checking voice status (GID:{guild_id})")
            if not queue.is_connected():
                print(f"[VOICE.STATUS] voice client not connected, reconnecting (GID:{guild_id})")
                try:
                    await queue.connect(ctx.author.voice.channel)
                except discord.ClientException as cEx:
                    print(f"[CONNECT.ERROR] unable to connect to VC:\n{cEx}")
                if queue.is_connected():
                    print(f"[VOICE.SUCCESS] voice client reconnected (GID:{guild_id})")
                else:
                    print(f"[VOICE.ERROR] voice client unable to reconnect, aborting and removing guild (GID:{guild_id})")
                    QueueManager.remove_queue(guild_id)
                    return await ctx.respond("Une erreur est survenu, je n'ai pas réussi à me reconnecter... veuillez réessayer ultérieurement")
                    
            voice_channel_queue = queue.get_voice_channel()
            if voice_channel_queue is not None and ctx.author.voice.channel != voice_channel_queue:
                await queue.move(ctx.author.voice.channel)
                print(f"[QUEUE.UPDATE.USER_HAS_MOVED] moved to new channel : {ctx.author.voice.channel} (GID:{guild_id})")
        
        # print("Guild (%d): Connected to %s (number of members: %d)" % (guild, Queues[guild].voice_client.channel.name, len(Queues[guild].voice_client.channel.members)))

        #new_entry: Entry = None
        


        play_cmd_transaction: MusicPlayCommandTransaction = MusicPlayCommandTransaction(ctx, self.bot)
        return await play_cmd_transaction.process_query(cmd_query)

#         # Query sanitizing
#         print(f"[QUERY.PROCESS] begin query processing on \"{cmd_query}\" (GID:{guild_id})")
#         # Append HTTPS to the link sent
#         if cmd_query.startswith("www."):
#             cmd_query = "https://" + cmd_query

#         queryType: PlayQueryType = self.analyse_query_type(cmd_query)


# #region Play_Spotify
#         if queryType is PlayQueryType.LINK_SPOTIFY:
#             if not config.spotifyEnabled:
#                 print(f"[SPOTIFY.DISABLED] Spotify research is disabled (GID:{guild_id})")
#                 return await ctx.respond(
#                     "La recherche Spotify n'est pas active",
#                     ephemeral = True)
            
#             print(f"[QUERY.PROCESS.SPOTIFY] begin spotify process on {cmd_query} (GID:{discordUserResponse.guild_ID})")
#             (is_spot_process_success, spot_process_return_string) = await self.spotify_process_url(cmd_query)

#             if not is_spot_process_success:
#                 return await ctx.respond(spot_process_return_string, ephemeral=True)
            
#             # spotify_result_type = self.analyse_query_type(spot_process_return_string)
#             # found_yt: bool = False
#             # if spotify_result_type is PlayQueryType.LINK_YOUTUBE:
#             #     #link gathered from song.link API
#             #     print(f"[QUERY.PROCESS.SPOTIFY.LINK] begin process of youtube link \"{spot_process_return_string}\" (GID:{discordUserResponse.guildID})")
#             #     await discordUserResponse.WriteUserResponse(f"Investigation sur \"{spot_process_return_string}\"...")
#             #     result = await self.youtube_process_link(spot_process_return_string)
#             #     found_yt = result is not None
#             #     if not found_yt:
#             #         # retry with query search
#             #         (is_spot_process_success, spot_process_return_string) =  self.spotify_process_url(cmd_query, True)
#             #         if not is_spot_process_success:
#             #             return await ctx.respond(spot_process_return_string, ephemeral=True)
#             #         spotify_result_type = self.analyse_query_type(spot_process_return_string)


#             # if spotify_result_type is PlayQueryType.SEARCH_QUERY:
#             #     #has fallback to 'lazy' youtube search
#             #     print(f"[QUERY.PROCESS.SPOTIFY.SEARCH] begin youtube search with query: \"{spot_process_return_string}\" (GID:{discordUserResponse.guildID})")
#             #     await discordUserResponse.WriteUserResponse(f"Recherche de \"{spot_process_return_string}\"...")
#             #     result = await self.youtube_process_search(spot_process_return_string)
#             # else:
#             #     print(f"[QUERY.PROCESS.SPOTIFY.ERROR] a link_conversion_fail happened on spotify_process of query: ({cmd_query})." +
#             #             f"\n\tProcess result is {spot_process_return_string} and new query type is {spotify_result_type.name} | (GID:{guild_id})")
#             #     return await ctx.respond("Une erreur est survenue lors du traitement du lien spotify (`link_conversion_fail`)", ephemeral=True)
#             if result is None:
#                 return await discordUserResponse.whisper_to_author("La recherche a échoué")
#             await discordUserResponse.whisper_to_author(f"Vidéo trouvée : **{(result['title'])}** de {(result['channel'])}, téléchargement...")
#             #TODO Download

# #endregion


#         elif queryType is PlayQueryType.LINK_YOUTUBE:
#             print(f"[QUERY.PROCESS.YOUTUBE.LINK] begin process of youtube link \"{yt_link}\" (GID:{discordUserResponse.guild_ID})")
#             result = await self.youtube_process_link(cmd_query)
#             try:
#                 data = result
#                 print(f"[YOUTUBE.SUCCESS] found link \"{(result['webpage_url'])}\" | (GID:{discordUserResponse.guild_ID})")
#             except Exception:
#                 print(f"[YOUTUBE.ERROR] link check failed\n\n{traceback.format_exc()} | (GID:{discordUserResponse.guild_ID})")
#                 return await discordUserResponse.whisper_to_author('Une erreur est survenue lors de la vérification du lien')
#             return await self.youtube_process_final(result)
        
#         elif queryType is PlayQueryType.SEARCH_QUERY:
#             print(f"[QUERY.PROCESS.SEARCH] begin youtube search with query: \"{search_query}\" (GID:{discordUserResponse.guild_ID})")
#             result = await self.youtube_process_search(cmd_query, discordUserResponse)
#             try:
#                 data = result
#                 print(f"[YOUTUBE.SUCCESS] found link \"{(result['webpage_url'])}\" | (GID:{discordUserResponse.guild_ID})")
#             except Exception:
#                 print(f"[YOUTUBE.ERROR] link check failed\n\n{traceback.format_exc()} | (GID:{discordUserResponse.guild_ID})")
#                 return await discordUserResponse.whisper_to_author('Une erreur est survenue lors de la vérification du lien')
#             return await self.youtube_process_final(result)

#         elif queryType is PlayQueryType.OTHER_STREAM:
#             new_entry = self.other_stream_process(cmd_query, discordUserResponse)
#             if new_entry is not None:
#                 position = await queue.add_entry(new_entry)
#                 return await ctx.respond(
#                     f"{position}: {cmd_query} a été ajouté à la file d\'attente",
#                     ephemeral=True)
#             else:
#                 print(f"[QUERY.PROCESS.OTHER.ERROR] An error happened while creating entry for ({cmd_query}) | (GID:{guild_id})")
#                 return await ctx.respond("Une erreur est survenue lors du traitement du lien (`entry_creation_fail`)", ephemeral=True)


#         else:
#             print(f"[QUERY.PROCESS.ERROR] error on creating entry for ({cmd_query}) | (GID:{guild_id})")
#             return await ctx.respond("Une erreur est survenue lors du traitement de la requête (`unknown_type_error`)", ephemeral=True)



#end region

    

#region old code
        # Other streams
        # if (cmd_query.startswith("http") or cmd_query.startswith("udp://")) and not cmd_query.startswith(("https://youtu.be", "https://www.youtube.com", "https://youtube.com")):
        #     print(f"[QUERY.PROCESS.OTHER] query \"{cmd_query}\" is another type of stream, may not work  (GID:{guild})")
        #     entry = Entry(cmd_query, ctx.author)
        #     entry.BuildMetaDataOtherStreams(cmd_query)
        #     position = await queue.add_entry(entry)
        #     return await ctx.respond(
        #         f"{position}: {cmd_query} a été ajouté à la file d\'attente",
        #         ephemeral=True)
        
        
        # YouTube Search
        # else:
        #     # Search query
        #     print(f"[QUERY.PROCESS.YOUTUBE] begin youtube processing on \"{cmd_query}\" (GID:{guild})")
        #     if not cmd_query.startswith("https://"):
        #         print(f"[YOUTUBE.SEARCH] begin youtube search with \"{cmd_query}\" (GID:{guild})")
        #         # message: discord.WebhookMessage = await ctx.respond(
        #         #     f"Recherche de \"{query}\"...",
        #         #     ephemeral=True)
        #         await discordUserResponse.WriteUserResponse(f"Recherche de \"{cmd_query}\"...")
        #         found: bool = False
        #         result = None
        #         # # Méthode youtube-search-python
        #         # try:
        #         #     result = await Youtube.searchVideos_YSP(query)
        #         #     if result is not None:
        #         #         found = True
        #         # except Exception:
        #         #     print("[YSP.SEARCH.ERROR] ysp.Search failed to find music, falling back to yt-dlp (GID:{guild})")
        #         #     # print(f"[FAILED SEARCH] ysp.Search failed to find music\n\n{traceback.format_exc()}")
        #         if not found:
        #             try:
        #                 result = await Youtube.searchVideosYT_DLP(cmd_query)
        #                 if result is not None:
        #                     found = True
        #             except Exception:
        #                 print(f"[YT-DLP.SEARCH.ERROR] yt-dlp.Search failed to find music (GID:{guild})\n\n{traceback.format_exc()}")

        #         if not found:
        #             return await discordUserResponse.WriteUserResponse("La recherche a échoué")
        #             # return await message.edit(content="La recherche a échoué")
        #         await discordUserResponse.WriteUserResponse(f"Vidéo trouvée : **{(result['title'])}** de {(result['channel'])}, téléchargement...")
        #         # await message.edit(content=f"Vidéo trouvée : **{(result['title'])}** de {(result['channel'])}, téléchargement...")

        #         # url = result["webpage_url"]
        #         # print(url)
        #     # Youtube Link
        #     else:
        #         print(f"[YOUTUBE.LINK] begin youtube search on link \"{cmd_query}\" (GID:{guild})")
        #         await discordUserResponse.WriteUserResponse(f"Investigation sur le lien \"{(cmd_query[len('https://'):])}\"...")
        #         # message: discord.WebhookMessage = await ctx.respond(
        #         #     f"Investigation sur le lien \"{(query[len('https://'):])}\"...",
        #         #     ephemeral=True)
        #         result = await Youtube.searchVideosYT_DLP(cmd_query)

        #     try:
        #         # data = await Youtube.fetchData(url, self.bot.loop)
        #         data = result
        #         print(f"[YOUTUBE.SUCCESS] found link \"{(result['webpage_url'])}\" (GID:{guild})")
        #     except Exception:
        #         print(f"[YOUTUBE.ERROR] link check failed\n\n{traceback.format_exc()} (GID:{guild})")
        #         return await discordUserResponse.WriteUserResponse('Une erreur est survenue lors de la vérification du lien')
        #         # return await message.edit('Une erreur est survenue lors de la vérification du lien')





        #     applicant = ctx.author

        #     if 'entries' in data:
        #         print(f"[YOUTUBE.PLAYLIST] playlist detected, extracting every entries (GID:{guild})")
        #         playlist = Playlist()
        #         playlist.buildMetadataYoutube(data)
        #         queue_start = Queues[guild].size
        #         for i in range(len(data['entries'])):
        #             if data['entries'][i] is not None:
        #                 if data['entries'][i]['is_live'] is True:
        #                     filename = data['entries'][i]['url']
        #                     file_size = 0
        #                 else:
        #                     try:
        #                         filename = Youtube.getFilename(data['entries'][i])
        #                         text = f"({i+1}/{len(data['entries'])}) Téléchargement de {data['entries'][i]['title']}..."
        #                         await Youtube.downloadAudio(
        #                             data['entries'][i]['webpage_url'],
        #                             discordUserResponse.message,
        #                             text,
        #                             self.bot.loop),
                            
        #                     except Exception:
        #                         print(f"[YOUTUBE.DOWNLOAD.ERROR] unable to download {data['entries'][i]['title']} (GID:{guild})\n\n{traceback.format_exc()}")
        #                         await discordUserResponse.WriteUserResponse(f"({i+1}/{len(data['entries'])}) Erreur lors du téléchargement de {data['entries'][i]['title']}")
        #                         # await message.edit(content=f"({i+1}/{len(data['entries'])}) Erreur lors du téléchargement de {data['entries'][i]['title']}")
        #                         continue

        #                     file_size = os.path.getsize(config.downloadDirectory + filename)


        #                 if Queues[guild].voice_client.is_connected():
        #                     entry = Entry(filename, applicant, file_size, playlist)
        #                     entry.buildMetadataYoutube(data['entries'][i])
        #                     position = await queue.add_entry(entry, queue_start + i)
        #                     #TODO bug when stopping the bot while a playlist is currently added in the queue, the bot will resume by itself by adding the next track to the queue
        #                     if i == len(data['entries']) - 1:
        #                         await discordUserResponse.WriteUserResponse(f"{data['title']} a été ajouté à la file d\'attente")
        #                         # await message.edit(content=f"{data['title']} a été ajouté à la file d\'attente")
        #                     else:
        #                         await discordUserResponse.WriteUserResponse(f"({i+1}/{len(data['entries'])}) {position}: {data['entries'][i]['title']} a été ajouté à la file d\'attente")
        #                         # await message.edit(content=f"({i+1}/{len(data['entries'])}) {position}: {data['entries'][i]['title']} a été ajouté à la file d\'attente")
        #                 else:
        #                     await discordUserResponse.WriteUserResponse("Téléchargement annulé")
        #                     # await message.edit(content="Téléchargement annulé")
        #                     break
        #     else:
        #         if data['is_live'] is True:
        #             filename = data['url']
        #             file_size = 0
        #         else:
        #             try:
        #                 await discordUserResponse.WriteUserResponse(f"Vidéo trouvée : **{(result['title'])}**")
        #                 # await message.edit(content=f"Vidéo trouvée : **{(result['title'])}**")
        #                 filename = Youtube.getFilename(data)
        #                 text = f"Téléchargement de {data['title']}..."
        #                 await Youtube.downloadAudio(
        #                     data['webpage_url'],
        #                     discordUserResponse.message,
        #                     text,
        #                     self.bot.loop)
        #                 file_size = os.path.getsize(config.downloadDirectory + filename)
        #             except Exception:
        #                 print(f"[YOUTUBE.DOWNLOAD.ERROR] unable to download {data['title']} (GID:{guild})\n\n{traceback.format_exc()}")
        #                 return await discordUserResponse.WriteUserResponse(f"Erreur lors du téléchargement de {data['title']}")
        #                 #return await message.edit(content=f"Erreur lors du téléchargement de {data['title']}")
                    

        #         if Queues[guild].voice_client.is_connected():
        #             entry = Entry(filename, applicant, file_size)
        #             entry.buildMetadataYoutube(data)
        #             position = await queue.add_entry(entry)
        #             await discordUserResponse.WriteUserResponse(f"{position}: {data['title']} a été ajouté à la file d\'attente")
        #             # await message.edit(content=f"{position}: {data['title']} a été ajouté à la file d\'attente")
        #             await ctx.send(f"{ctx.author.display_name} a ajouté une musique…")
        #         else:
        #             print(f"[CONNECT.ERROR] Trying to add music but voice_client is not connected (GID:{guild})")

#endregion



#region player cmds
    #TODO UNTESTED
    async def seek(self, ctx: discord.ApplicationContext, timeCode: str = None):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)

        if queue is None:
            return await ctx.respond("Pas de lecture en cours", ephemeral=True)

        currentEntry = queue.content[queue.cursor]
        if currentEntry.duration <= 0:
            return await ctx.respond("Ce morceau n'est pas seekable", ephemeral=True)

        #Decoding timeCode
        try:
            time = list(map(int, timeCode.split(":")))[::-1]
        except:
            return await ctx.respond("Quelque chose ne va pas dans la syntaxe (doit être hhhh:mm:ss ou mmmm:ss ou bien ssss)", ephemeral=True)
        (secs, mins, hrs) = (0,0,0)
        secs = time[0]
        if len(time) > 1:
            if 0 <= secs < 60:
                mins = time[1]
            else: #TODO specify error
                return await ctx.respond("Le temps n'est pas conforme", ephemeral=True)
            if len(time) > 2:
                if  0 <= mins < 60:
                    hrs = time[2]
                else:
                    return await ctx.respond("Le temps n'est pas conforme", ephemeral=True)
                if hrs < 0:
                    return await ctx.respond("Le temps n'est pas conforme", ephemeral=True)
        desiredStart = secs + 60*mins + 60*60*hrs
        
        if 0 <= desiredStart < currentEntry.duration -1:
            queue.next_entry_condition = NextEntryCondition.SEEK
            queue.seek_time = desiredStart
            queue.stop()
            return await ctx.respond(f"Utilisation de Seek:tm: !", ephemeral=True) #TODO better response
        else:
            return await ctx.respond(f"La vidéo sera déjà finie à {time_format(desiredStart)}...", ephemeral=True)


    #TODO UNTESTED
    async def pause(self, ctx: discord.ApplicationContext):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)
        
        if queue is not None:
            if queue.is_playing():
                queue.pause()
                queue.pausetime = time.time()
                print(f"[MUSIC.PAUSE] paused listening (GID:{queue.guild_id})")
                return await ctx.respond("Lecture mise en pause")
            else:
                return await ctx.respond("Lecture déjà en pause !", ephemeral=True)
        else:
            print(f"[MUSIC.PAUSE.ERROR] pause() called but not in the registered guilds (GID:{queue.guild_id})")
            return await ctx.respond("Selon les informations que je possède, il n'y a aucune lecture en cours sur ce serveur", ephemeral=True)


    #TODO UNTESTED
    async def resume(self, ctx: discord.ApplicationContext):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)
        if queue is not None:
            if queue.is_paused():
                queue.resume()
                queue.starttime = time.time() - (queue.pausetime - queue.starttime) # Setting starttime to the correct time to ensure that the time elapsed on the entry is correct when resuming
                queue.pausetime = 0
                print(f"[MUSIC.RESUME] resumed listening (GID:{queue.guild_id})")
                return await ctx.respond("Reprise de la lecture")
            else:
                return await ctx.respond("On est déjà en lecture !", ephemeral=True)
        else:
            print(f"[MUSIC.RESUME.ERROR] resume() called but not in the registered guilds (GID:{queue.guild_id})")
            return await ctx.respond("Selon les informations que je possède, il n'y a aucune lecture en cours sur ce serveur", ephemeral=True)

    #TODO UNTESTED
    async def stop(self, ctx: discord.ApplicationContext):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)
        
        if queue.has_voice_client():
            if queue.is_playing or queue.is_paused:
                if ctx.author.voice is None or ctx.author.voice.channel != queue.get_voice_channel():
                    return await ctx.respond("Je suis en train de jouer de la musique là, viens me le dire en face !", ephemeral=True)
                queue.next_entry_condition = NextEntryCondition.STOP
                queue.repeat_bypass = True
                queue.stop()
                print(f"[MUSIC.STOP] stopped listening (GID:{queue.guild_id})")
                return await ctx.respond("Ok j'arrête de lire la musique :(")
        else:
            print(f"[MUSIC.STOP.ERROR] stop() called but not in the registered guilds (GID:{queue.guild_id})")
            return await ctx.respond("Selon les informations que je possède, je suis pas connecté sur ce serveur.", ephemeral=True)

#endregion





#region entry info
    #TODO UNTESTED
    async def info(self, ctx: discord.ApplicationContext, index: int):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)

        if queue is None:
            return await ctx.respond("Aucune liste de lecture", ephemeral=True)
        
        if index >= queue.size and index < 0:
            return await ctx.respond('L\'index %d n\'existe pas' % (index), ephemeral=True)
        
        entry = queue.content[index]

#region old code
        # content = ""

        # if hasattr(entry, 'like_count') and hasattr(entry, 'view_count'):
        #     content += f"{(entry.view_count)} vues | {entry.like_count} likes\n"

        # if hasattr(entry, 'channel') and hasattr(entry, 'channel_url'):
        #     content += f"Chaîne : [{entry.channel}]({entry.channel_url})"
        #     if hasattr(entry, 'channel_follower_count'):
        #         content += f" ({entry.channel_follower_count} abonnés)"
        #     content += "\n\n"

        # if Queues[guild].cursor == index:
        #     pause: str = "[Paused]" if Queues[guild].voice_client.is_paused() else ""
        #     current: float = Queues[guild].pausetime - Queues[guild].starttime if Queues[guild].voice_client.is_paused() else time.time() - Queues[guild].starttime
            
        #     if not hasattr(entry, 'duration'): #Other Stream
        #         content += f"Durée d'écoute : {time_format(current)} {pause}\n\n"
        #     else: #File
        #         content += f"Progression : {time_format(current)}/{time_format(entry.duration)} {pause}\n"
                
        #         #Progress bar
        #         progress = (current/entry.duration)*20
        #         content += "["
        #         for i in range(0,20):
        #             if int(progress) == i:
        #                 content += "●"
        #             else:
        #                 content += "─"
        #         content += f"] ({int((current/entry.duration)*100)}%)\n\n"

        # if hasattr(entry, 'album'):
        #     content += f"Album : {entry.album}\n\n"
        # if hasattr(entry, 'playlist'):
        #     if entry.playlist is not None :
        #         content += f"Playlist : [{entry.playlist.title}]({entry.playlist.url})\n\n"
        # content += f"Position dans la queue : {index}"



        # embed = discord.Embed(
        #     title = entry.title,
        #     url = entry.url,
        #     description = content,
        #     color = 0x565493
        # )

        # # embed_dict = {
        # #     "title" : entry.title,
        # #     "url" : entry.url,
        # #     "video" : {"url" : entry.url, "height" : 200, "width" : 200},
        # #     "description" : content,
        # #     "color" : 0x565493
        # # }

        # # embed = discord.Embed.from_dict(embed_dict)

        

        # # if entry.is_youtube:
        # #     if hasattr(entry, 'url'):
        # #         embed.video = 
        # if hasattr(entry, 'thumbnail'):
        #     embed.set_image(url = entry.thumbnail)
        # #embed.set_thumbnail(url=self.bot.user.avatar.url)
        # embed.set_footer(text = "Demandé par %s" % entry.applicant.display_name, icon_url = entry.applicant.display_avatar.url)
#endregion

        #TODO modify into a Queue method
        embed: discord.Embed = EmbedBuilder.build_embed(entry, queue)
        if queue.cursor == index:
            play_status = " ❚❚" if queue.is_paused() else " ▶"
            name = play_status + "\t" + (" En pause" if queue.is_paused() else " En cours de lecture")
        else:
            name = "Informations piste"
        embed.set_author(name = name, icon_url = self.bot.user.display_avatar.url)
        return await ctx.respond(embed=embed)


    #TODO UNTESTED
    async def now_playing(self, ctx: discord.ApplicationContext):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)
        if queue is None or queue.cursor == queue.size:
            return await ctx.respond(
                'Rien en lecture',
                ephemeral=True)
        else:
            await self.info(ctx, queue.cursor)

#endregion





#region queue cmds
    async def print_queue(self, ctx: discord.ApplicationContext, page:int = None):

        queue: Queue = QueueManager.get_queue(ctx.guild.id)
        if queue is None:
            return await ctx.respond('Aucune liste de lecture sur ce serveur', ephemeral=True)


        total_duration = 0
        total_size = 0
        current_playlist = ""
        queue_list = ""
        

        #TODO add this to the config file
        print_size = 20
        print_min, print_max = 0, queue.size #default values
        
        if page is None:
            print_min = max(queue.cursor - print_size // 2, 0)
            print_max = min(print_min + print_size, queue.size)
        else:
            if (page - 1) * print_size > queue.size or page < 1:
                return await ctx.respond('Index de page invalide', ephemeral=True)
            
            print_min = (page - 1)*print_size
            print_max = min(print_min + print_size, queue.size)
        
        if print_min == 0:
            queue_list += "==== Début de la file\n"
        else:
            queue_list += "⠀⠀⠀⠀…\n"
            
        for index in range(print_min, print_max):
            entry: Entry = queue.content[index]
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

            
            
            current_playlist = ""

            #TODO ???
            if entry.playlist is not None:
                tab = "⠀⠀⠀⠀"
                if entry.playlist.id != current_playlist:
                    current_playlist = entry.playlist.id
                    if queue.repeat_mode == RepeatMode.PLAYLIST:
                        queue_list += "⟳ ⠀"
                    else:
                        queue_list += "⠀⠀ "
                    queue_list += f" Playlist : {entry.playlist.title}\n"
                
            
            

            queue_list += f"{tab}{indicator}{index}: {title} - {time_format(duration)}\n"

            
            # totalSize += entry.fileSize


        if print_max == queue.size:
            queue_list += "==== Fin de la file"
        else:
            queue_list += "⠀⠀⠀⠀…"
        
        repeat_text = {
            RepeatMode.NO_REPEAT: "Aucun",
            RepeatMode.ENTRY: "Musique en cours",
            RepeatMode.ALL: "Liste de lecture",
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

        return await ctx.respond(embed=embed)
    

    
    async def move(self, ctx: discord.ApplicationContext, frm: int, to: int):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)
        if queue is None:
            return await ctx.respond("Aucune liste de lecture", ephemeral=True)

        if frm == to:
            return await ctx.respond('La destination ne peut pas être égale à la source', ephemeral=True)

        if frm < queue.size and frm >= 0 and to < queue.size and to >= 0:
            moved_entry_title = queue.get_entry(frm).title
            queue.move_entry(frm, to)

            #global announce
            await ctx.respond(f"La piste n°{frm} a été déplacé à la position {to}")
            #user response
            await ctx.respond(f"{moved_entry_title} a été déplacé de {frm} vers {to}", ephemeral=True)
            return
        else:
            return await ctx.respond("Une des deux positions est invalide", ephemeral=True)


    async def remove(self, ctx: discord.ApplicationContext, idx1: int, idx2: int = None):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)
        
        if queue is None:
            return await ctx.respond("Aucune liste de lecture", ephemeral=True)
                    
        if idx1 >= queue.size or idx1 < 0:
            return await ctx.respond(f"L'index 1 ({idx1}) n'existe pas dans la queue", ephemeral=True)
        
        if idx2 is None: # remove one entry
            entry = queue.get_entry(idx1)
            # stop playback if current entry is being removed
            if idx1 == queue.cursor:
                queue.stop()
            queue.remove_entry(idx1)
            # move cursor if removed item was before
            if idx1 <= queue.cursor:
                queue.cursor -= 1
            # remove associated file
            if entry.filename in os.listdir(config.downloadDirectory):
                os.remove(config.downloadDirectory + entry.filename)
            print(f"[MUSIC.REMOVE] Entry number {idx1} has been removed (GID:{queue.guild_id})")
            return await ctx.respond(f"{entry.title} a bien été supprimé")
        
        else: # remove multiple entries
            oldSize = queue.size
            # index checks
            if idx2 >= oldSize or idx2 < 0:
                return await ctx.respond(f"L'index 2 ({idx2}) n'existe pas dans la liste de lecture", ephemeral=True)
            if idx1 > idx2:
                return await ctx.respond("Attention à l'ordre des index !", ephemeral=True)
            
            if idx1 <= queue.cursor <= idx2:
                queue.pause()

            for i in range(idx2 - idx1 + 1):
                entry = queue.get_entry(idx1)
                queue.remove_entry(idx1)
                if idx1 <= queue.cursor:
                    queue.cursor -= 1
                if entry.filename in os.listdir(config.downloadDirectory):
                    os.remove(config.downloadDirectory + entry.filename)
            
            queue.stop()
            print(f"[MUSIC.REMOVE] Entries in range ({idx1} - {idx2}) have been removed (GID:{queue.guild_id})")
            return await ctx.respond(f"Les entrées commençant à {idx1} jusqu'à {('la fin de la liste' if idx2 == oldSize else str(idx2))} ont bien été supprimés")
        


    
    async def skip(self, ctx: discord.ApplicationContext):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)

        if queue is not None:
            if queue.cursor < queue.size:
                queue.next_entry_condition = NextEntryCondition.SKIP
                queue.repeat_bypass = True
                queue.cursor = queue.cursor + 1
                queue.stop()
                return await ctx.respond("Passage à la musique suivante")
            else:
                return await ctx.respond('Nous sommes à la fin de la liste de lecture', ephemeral=True)
        else:
            return await ctx.respond('Aucune liste de lecture sur ce serveur', ephemeral=True)

#endregion





    async def leave(self, ctx: discord.ApplicationContext):
        guild_id = ctx.guild.id

        guild_queue: Queue = QueueManager.get_queue(guild_id)

        if guild_queue is None or not guild_queue.has_voice_client():
            voice_client: discord.VoiceClient = self.__get_voice_client_from_guild(guild_id)
            if voice_client is not None:
                await voice_client.disconnect()
                voice_client.cleanup()
                print(f"[MUSIC.LEAVE] Disconnected lone voice_client (GID:{guild_id})")
                return await ctx.respond('Ok bye!')
            else:
                print(f"[MUSIC.LEAVE.ERROR] leave() called but not in the registered guilds (GID:{guild_id})")
                return await ctx.respond("Selon les informations que je possède, je suis pas connecté sur ce serveur.", ephemeral=True)
        

        if guild_queue.is_playing() and (ctx.author.voice is None or ctx.author.voice.channel != guild_queue.get_voice_channel()):
            return await ctx.respond("Je suis en train de jouer de la musique là, viens me le dire en face !", ephemeral=True)
        guild_queue.next_entry_condition = NextEntryCondition.STOP
        guild_queue.stop()
        await guild_queue.disconnect_and_cleanup()
        print(f"[MUSIC.LEAVE] Disconnected voice_client (GID:{guild_id})")
        await asyncio.sleep(0.2)
        for entry in guild_queue.content:
            if entry.filename in os.listdir(config.downloadDirectory):
                try:
                    os.remove(config.downloadDirectory + entry.filename) # If running on Windows), the file currently playing will not be erased
                except:
                    print(f"[MUSIC.LEAVE.CLEANUP.ERROR] error while removing file \"{entry.filename}\" (GID:{guild_id})")
                    continue
        await QueueManager.remove_queue(guild_id)
        return await ctx.respond('Ok bye!')
        # else:
        #     print(f"[MUSIC.LEAVE.ERROR] leave() called but voice client is None (GID:{guild_id})")
        #     return await ctx.respond("Selon les informations que je possède, je suis pas connecté sur ce serveur.", ephemeral=True)


    async def repeat(self, ctx: discord.ApplicationContext, mode: str):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)

        if queue is None:
            return await ctx.respond("Aucune liste de lecture", ephemeral=True)

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
                    return await ctx.respond(f":warning: `{mode}` n'est pas un mode de répétition existant", ephemeral=True)
            return await ctx.respond(f"Le mode de répétition à été changé sur `{repeat_text[queue.repeat_mode]}`")
        else:
            repeat_modes = [RepeatMode.NO_REPEAT, RepeatMode.ENTRY, RepeatMode.PLAYLIST, RepeatMode.ALL]
            old_mode = queue.repeat_mode
            new_mode = repeat_modes[(repeat_modes.index(old_mode) + 1) % len(repeat_modes)]
            queue.repeat_mode = new_mode
            return await ctx.respond(f"Le mode de répétition à été changé sur `{new_mode}`")

    
    async def goto(self, ctx: discord.ApplicationContext, index: int):
        queue: Queue = QueueManager.get_queue(ctx.guild.id)

        if queue is None:
            return await ctx.respond("Aucune liste de lecture", ephemeral=True)
        
        if not queue.has_voice_client():
            print("[MUSIC.GOTO.ERROR] guild(%d) has no VoiceClient")
            #TODO Handle queue tests (maybe in a separate method)
            return await ctx.respond(":warning: Une erreur est survenue lors de la commande", ephemeral=True)

        if index < queue.size and index >= 0:
            queue.cursor = index
            if queue.is_playing() or queue.is_paused():
                queue.repeat_bypass = True
                queue.stop()
            else:
                await queue.start_playback()
            return  await ctx.respond(f"Direction la musique n°{index}")
        else:
            return await ctx.respond(f"L'index {index} n'existe pas", ephemeral=True)


    async def __vc_connection_test(self, ctx: discord.ApplicationContext) -> discord.VoiceClient:
        voice_client: discord.VoiceClient = ctx.voice_client
        if voice_client is None:
            pass


    async def __initialize_queue(self, ctx: discord.ApplicationContext):
        guild_id = ctx.guild.id
        new_queue: Queue = QueueManager.create_queue(guild_id, None, ctx.channel)
        print(f"[QUEUE.INIT] New queue added, attempting connection (GID:{guild_id})")
        await new_queue.connect(ctx.author.voice.channel)

        print(f"[CONNECT.SUCCESS] new connection to channel {ctx.author.voice.channel.name} (GID:{guild_id})")
        await asyncio.sleep(0.2)

        #Adding startup sound
        check, file = pick_sound_file("startup")
        if check:
            if file != "":
                new_entry = Entry("Booting up...", self.bot.user, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                new_entry.add_image("https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/3ddaa372-c58c-4587-911e-1d625dff64dc/dapv26n-b138c16c-1cfc-45c3-9989-26fcd75d3060.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3sicGF0aCI6IlwvZlwvM2RkYWEzNzItYzU4Yy00NTg3LTkxMWUtMWQ2MjVkZmY2NGRjXC9kYXB2MjZuLWIxMzhjMTZjLTFjZmMtNDVjMy05OTg5LTI2ZmNkNzVkMzA2MC5qcGcifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6ZmlsZS5kb3dubG9hZCJdfQ.PnU42OFMHcio7nJ4a5Jsp8C-d6exHqd3vInU1682x1E")
                new_entry.add_description("Chaîne : [DJPatrice](https://github.com/Kumkwats/DJscord)")
                new_entry.map_to_file(file)
                await new_queue.add_entry(new_entry)
                print(f"[QUEUE.STARTUP] Startup file added to queue (GID:{guild_id})")
            else:
                print(f"[QUEUE.STARTUP] Aucun fichier trouvé (GID:{guild_id})")
        else:
            print(f"[QUEUE.STARTUP] Dossier Sounds inexistant (GID:{guild_id})")

        return new_queue

    def __create_boot_entry(self) -> Entry | None:
        check, file = pick_sound_file("startup")
        if check:
            if file != "":
                new_entry = Entry("Booting up...", self.bot.user, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                new_entry.add_image("https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/3ddaa372-c58c-4587-911e-1d625dff64dc/dapv26n-b138c16c-1cfc-45c3-9989-26fcd75d3060.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3sicGF0aCI6IlwvZlwvM2RkYWEzNzItYzU4Yy00NTg3LTkxMWUtMWQ2MjVkZmY2NGRjXC9kYXB2MjZuLWIxMzhjMTZjLTFjZmMtNDVjMy05OTg5LTI2ZmNkNzVkMzA2MC5qcGcifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6ZmlsZS5kb3dubG9hZCJdfQ.PnU42OFMHcio7nJ4a5Jsp8C-d6exHqd3vInU1682x1E")
                new_entry.add_description("Chaîne : [DJPatrice](https://github.com/Kumkwats/DJscord)")
                new_entry.map_to_file(file)
                print(f"[QUEUE.STARTUP] Startup file added to queue")
                return new_entry
            else:
                print(f"[QUEUE.STARTUP] Aucun fichier trouvé")
        else:
            print(f"[QUEUE.STARTUP] Dossier Sounds inexistant")

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
                print(f"Timeout: [INFO] Guild ({guild_queue}) has no voice_client, will be removed")
            else:
                if guild_queue.is_playing():
                    guild_queue.update_last_voice_activity()
                else:
                    if time.time() - guild_queue.last_voice_activity_time >= config.afkLeaveTime*60:
                        guilds_to_disconnect.append(guild_id)
                        print(f"Timeout: [INFO] Guild ({guild_id}) has been inactive for too long, will be removed (AFK time = {time.time() - guild_queue.last_voice_activity_time} seconds)")
                        
        
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
                        print("Timeout: No file in Leave folder")
                else:
                    print("PickSound: dossier Sounds inexistant")
                    
                while guild_to_disconnect.__voice_client.is_playing():
                    await asyncio.sleep(0.1)

                await guild_to_disconnect.disconnect_and_cleanup()
                await QueueManager.remove_queue(guild_id)
                print(f"Guild ({guild_queue}): Disconnected for inactivity")

#endregion
