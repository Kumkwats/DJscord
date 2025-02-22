import os
import asyncio
import time
import random
import traceback



import discord
from discord.ext import tasks, commands



from DJscordBot.entities import Entry, Playlist, Queue, NextEntryCondition
from DJscordBot.utils import time_format, pick_sound_file
from DJscordBot.config import config

from DJscordBot.ServicesClients.youtube import Youtube
from DJscordBot.ServicesClients.spotify import Spotify
# from help import Help



VOICE_ACTIVITY_CHECK_DELTA = 5 #number of seconds between every AFK check

Queues: 'dict[int, Queue]' = {}




class Music():
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        if config.afkLeaveActive:
            self.music_timeout.start()

    async def play(self, ctx: discord.ApplicationContext, query: str):
        await ctx.defer(ephemeral=True)

        guild = ctx.guild.id
        author_voice = ctx.author.voice
        if author_voice is None: # Not connected
            print(f"[CONNECT.ERROR] no author_voice, cannot connect (GID:{guild})")
            return await ctx.respond(
                "Vous n'êtes pas connectés à un salon vocal", 
                ephemeral=True)
        
        
        author_text = ctx.channel

        #New Guild
        if guild not in Queues: 
            print(f"[QUEUE] new queue added, trying connection (GID:{guild})")
            Queues[guild] = Queue(guild, None, author_text)
            Queues[guild].voice_client = await author_voice.channel.connect(
                timeout=600,
                reconnect=True)

            print(f"[CONNECT.SUCCESS] new connection to channel {author_voice.channel.name} (GID:{guild})")

            #Only add the startup sound if there is no queue
            check, file = pick_sound_file("startup")
            if check:
                if file != "":
                    entry = Entry(file, self.bot.user)
                    entry.title = "Booting up..."
                    entry.channel = "DJPatrice"
                    entry.channel_url = "https://github.com/Kumkwats/DJscord"
                    entry.duration = 0
                    entry.album = None
                    entry.thumbnail = "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/3ddaa372-c58c-4587-911e-1d625dff64dc/dapv26n-b138c16c-1cfc-45c3-9989-26fcd75d3060.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3sicGF0aCI6IlwvZlwvM2RkYWEzNzItYzU4Yy00NTg3LTkxMWUtMWQ2MjVkZmY2NGRjXC9kYXB2MjZuLWIxMzhjMTZjLTFjZmMtNDVjMy05OTg5LTI2ZmNkNzVkMzA2MC5qcGcifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6ZmlsZS5kb3dubG9hZCJdfQ.PnU42OFMHcio7nJ4a5Jsp8C-d6exHqd3vInU1682x1E"
                    entry.url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

                    await Queues[guild].add_entry(entry)
                    print(f"[QUEUE.STARTUP] Startup file added to queue (GID:{guild})")
                else:
                    print(f"[QUEUE.STARTUP] Aucun fichier trouvé (GID:{guild})")
            else:
                print(f"[QUEUE.STARTUP] Dossier Sounds inexistant (GID:{guild})")
        #Existing queue checks
        else:
            print(f"[QUEUE] existing queue, checking voice status (GID:{guild})")
            if not Queues[guild].voice_client.is_connected():
                print(f"[VOICE.STATUS] voice client not connected, reconnecting (GID:{guild})")
                await Queues[guild].connect(author_voice.channel)
                if Queues[guild].voice_client.is_connected():
                    print(f"[VOICE.SUCCESS] voice client reconnected (GID:{guild})")
                else:
                    Queues.pop(guild)
                    print(f"[VOICE.ERROR] voice client unable to reconnect, aborting and removing guild (GID:{guild})")
                    return await ctx.respond(
                        "Une erreur est survenu, je n'ai pas réussi à me reconnecter... veuillez réessayer ultérieurement")
                    

            if author_voice.channel != Queues[guild].voice_client.channel:
                await Queues[guild].move(author_voice.channel)
                print(f"[USER_HAS_MOVED] moved to new channel : {author_voice.channel} (GID:{guild})")
        
        # print("Guild (%d): Connected to %s (number of members: %d)" % (guild, Queues[guild].voice_client.channel.name, len(Queues[guild].voice_client.channel.members)))


        queue = Queues[guild]
        entry = None



        # Query processing
        print(f"[QUERY.PROCESS] begin query processing on \"{query}\" (GID:{guild})")
        # Append HTTPS to the link sent
        if query.startswith("www."):
            query = "https://" + query


        # Spotify Search
        if query.startswith(("spotify:", "https://open.spotify.com/")):
            if not config.spotifyEnabled:
                print(f"[SPOTIFY.DISABLED] Spotify research is disabled (GID:{guild})")
                return await ctx.respond(
                    'La recherche Spotify n\'a pas été configurée',
                    ephemeral = True)
            
            print(f"[QUERY.PROCESS.SPOTIFY] begin spotify search on {query} (GID:{guild})")
            if query.startswith("https://open.spotify.com/"):
                query = query[len("https://open.spotify.com/"):].replace('/', ':')
            else:
                query = query[len("spotify:"):]

            try:
                splitedQuery = query.split(':')
                if(len(splitedQuery) == 2):
                    [_type, _id] = splitedQuery
                else:
                    [_misc, _type, _id] = splitedQuery

                if _type == 'track':
                    track = Spotify.getTrack(_id)
                    query = f"{track['name']} {track['artists'][0]['name']}"
                    print(f"[SPOTIFY.SUCCESS] track found, passing to youtube search (GID:{guild})")
                elif _type == 'playlist':
                    print(f"[SPOTIFY.NOT_IMPLEMENTED] Spotify playlists are not implemented (GID:{guild})")
                    return await ctx.respond('Les playlists Spotify ne sont melheureusement pas pris en charge', ephemeral=True)
                else:
                    print(f"[SPOTIFY.UNHANDLED] type \"{_type}\" is not handled (GID:{guild})")
                    return await ctx.respond('Une erreur est survenue, vérifier bien que le lien spotify dirige vers une musique', ephemeral=True)
            except Exception:
                print(f"[SPOTIFY.ERROR] Spotify search failed to find music\n\n{traceback.format_exc()}")
                return await ctx.respond('Le lien Spotify est invalide', ephemeral=True)

        
        # Other streams
        if (query.startswith("http") or query.startswith("udp://")) and not query.startswith(("https://youtu.be", "https://www.youtube.com", "https://youtube.com")):
            print(f"[QUERY.PROCESS.OTHER] query \"{query}\" is another type of stream, may not work  (GID:{guild})")
            entry = Entry(query, ctx.author)
            entry.BuildMetaDataOtherStreams(query)
            position = await queue.add_entry(entry)
            return await ctx.respond(
                f"{position}: {query} a été ajouté à la file d\'attente",
                ephemeral=True)
        
        
        # YouTube Search
        else:
            # Search query
            print(f"[QUERY.PROCESS.YOUTUBE] begin youtube processing on \"{query}\" (GID:{guild})")
            if not query.startswith("https://"):
                print(f"[YOUTUBE.SEARCH] begin youtube search with \"{query}\" (GID:{guild})")
                message: discord.WebhookMessage = await ctx.respond(
                    f"Recherche de \"{query}\"...",
                    ephemeral=True)
                found: bool = False
                result = None
                # # Méthode youtube-search-python
                # try:
                #     result = await Youtube.searchVideos_YSP(query)
                #     if result is not None:
                #         found = True
                # except Exception:
                #     print("[YSP.SEARCH.ERROR] ysp.Search failed to find music, falling back to yt-dlp (GID:{guild})")
                #     # print(f"[FAILED SEARCH] ysp.Search failed to find music\n\n{traceback.format_exc()}")
                if not found:
                    try:
                        result = await Youtube.searchVideosYT_DLP(query)
                        if result is not None:
                            found = True
                    except Exception:
                        print(f"[YT-DLP.SEARCH.ERROR] yt-dlp.Search failed to find music (GID:{guild})\n\n{traceback.format_exc()}")

                if not found:
                    return await message.edit(content="La recherche a échoué")
                await message.edit(content=f"Vidéo trouvée : **{(result['title'])}** de {(result['channel'])}, téléchargement...")

                # url = result["webpage_url"]
                # print(url)
            # Youtube Link
            else:
                print(f"[YOUTUBE.LINK] begin youtube search on link \"{query}\" (GID:{guild})")
                message: discord.WebhookMessage = await ctx.respond(
                    f"Investigation sur le lien \"{(query[len('https://'):])}\"...",
                    ephemeral=True)
                result = await Youtube.searchVideosYT_DLP(query)


            #TODO qu'est-ce que c'est que ce truc ?
            try:
                # data = await Youtube.fetchData(url, self.bot.loop)
                data = result
                print(f"[YOUTUBE.SUCCESS] found link \"{(result['webpage_url'])}\" (GID:{guild})")
            except Exception:
                print(f"[YOUTUBE.ERROR] link check failed\n\n{traceback.format_exc()} (GID:{guild})")
                return await message.edit('Une erreur est survenue lors de la vérification du lien')

            applicant = ctx.author

            if 'entries' in data:
                print(f"[YOUTUBE.PLAYLIST] playliste detected, extracting every entries (GID:{guild})")
                playlist = Playlist()
                playlist.buildMetadataYoutube(data)
                queue_start = Queues[guild].size
                for i in range(len(data['entries'])):
                    if data['entries'][i] is not None:
                        if data['entries'][i]['is_live'] is True:
                            filename = data['entries'][i]['url']
                            file_size = 0
                        else:
                            try:
                                filename = Youtube.getFilename(data['entries'][i])
                                text = f"({i+1}/{len(data['entries'])}) Téléchargement de {data['entries'][i]['title']}..."
                                await Youtube.downloadAudio(
                                    data['entries'][i]['webpage_url'],
                                    message,
                                    text,
                                    self.bot.loop),
                            
                            except Exception:
                                print(f"[YOUTUBE.DOWNLOAD.ERROR] unable to download {data['entries'][i]['title']} (GID:{guild})\n\n{traceback.format_exc()}")
                                await message.edit(content=f"({i+1}/{len(data['entries'])}) Erreur lors du téléchargement de {data['entries'][i]['title']}")
                                continue

                            file_size = os.path.getsize(config.downloadDirectory + filename)


                        if Queues[guild].voice_client.is_connected():
                            entry = Entry(filename, applicant, file_size, playlist)
                            entry.buildMetadataYoutube(data['entries'][i])
                            position = await queue.add_entry(entry, queue_start + i)
                            #TODO bug when stopping the bot while a playlist is currently added in the queue, the bot will resume by itself by adding the next track to the queue
                            if i == len(data['entries']) - 1:
                                await message.edit(content=f"{data['title']} a été ajouté à la file d\'attente")
                            else:
                                await message.edit(content=f"({i+1}/{len(data['entries'])}) {position}: {data['entries'][i]['title']} a été ajouté à la file d\'attente")
                        else:
                            await message.edit(content="Téléchargement annulé")
                            break
            else:
                if data['is_live'] is True:
                    filename = data['url']
                    file_size = 0
                else:
                    try:
                        await message.edit(content=f"Vidéo trouvée : **{(result['title'])}**")
                        filename = Youtube.getFilename(data)
                        text = f"Téléchargement de {data['title']}..."
                        await Youtube.downloadAudio(data['webpage_url'], message, text, self.bot.loop)
                        file_size = os.path.getsize(config.downloadDirectory + filename)
                    except Exception:
                        print(f"[YOUTUBE.DOWNLOAD.ERROR] unable to download {data['entries'][i]['title']} (GID:{guild})\n\n{traceback.format_exc()}")
                        return await message.edit(content=f"Erreur lors du téléchargement de {data['title']}")
                    

                if Queues[guild].voice_client.is_connected():
                    entry = Entry(filename, applicant, file_size)
                    entry.buildMetadataYoutube(data)
                    position = await queue.add_entry(entry)
                    await message.edit(content=f"{position}: {data['title']} a été ajouté à la file d\'attente")
                    await ctx.send(f"{ctx.author.display_name} a ajouté une musique…")
                else:
                    print(f"[CONNECT.ERROR] Trying to add music but voice_client is not connected (GID:{guild})")

    async def now_playing(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id
        if guild not in Queues or Queues[guild].cursor == Queues[guild].size:
            return await ctx.respond(
                'Rien en lecture',
                ephemeral=True)
        else:
            await self.info(ctx, Queues[guild].cursor)

    async def info(self, ctx: discord.ApplicationContext, index: int):
        guild = ctx.guild.id
        if guild not in Queues:
            return await ctx.respond(
                'Aucune liste d\'attente',
                ephemeral=True)

        #Queues[guild].voice_client = ctx.voice_client
        
        if index >= Queues[guild].size and index < 0:
            return await ctx.respond('L\'index %d n\'existe pas' % (index), ephemeral=True)
        
        entry = Queues[guild].content[index]


        content = ""

        if hasattr(entry, 'like_count') and hasattr(entry, 'view_count'):
            content += f"{(entry.view_count)} vues | {entry.like_count} likes\n"

        if hasattr(entry, 'channel') and hasattr(entry, 'channel_url'):
            content += f"Chaîne : [{entry.channel}]({entry.channel_url})"
            if hasattr(entry, 'channel_follower_count'):
                content += f" ({entry.channel_follower_count} abonnés)"
            content += "\n\n"

        if Queues[guild].cursor == index:
            pause: str = "[Paused]" if Queues[guild].voice_client.is_paused() else ""
            current: float = Queues[guild].pausetime - Queues[guild].starttime if Queues[guild].voice_client.is_paused() else time.time() - Queues[guild].starttime
            
            if not hasattr(entry, 'duration'): #Other Stream
                content += f"Durée d'écoute : {time_format(current)} {pause}\n\n"
            else: #File
                content += f"Progression : {time_format(current)}/{time_format(entry.duration)} {pause}\n"
                
                #Progress bar
                progress = (current/entry.duration)*20
                content += "["
                for i in range(0,20):
                    if int(progress) == i:
                        content += "●"
                    else:
                        content += "─"
                content += f"] ({int((current/entry.duration)*100)}%)\n\n"

        if hasattr(entry, 'album'):
            content += f"Album : {entry.album}\n\n"
        if hasattr(entry, 'playlist'):
            if entry.playlist is not None :
                content += f"Playlist : [{entry.playlist.title}]({entry.playlist.url})\n\n"
        content += f"Position dans la queue : {index}"



        embed = discord.Embed(
            title = entry.title,
            url = entry.url,
            description = content,
            color = 0x565493
        )

        # embed_dict = {
        #     "title" : entry.title,
        #     "url" : entry.url,
        #     "video" : {"url" : entry.url, "height" : 200, "width" : 200},
        #     "description" : content,
        #     "color" : 0x565493
        # }

        # embed = discord.Embed.from_dict(embed_dict)

        if Queues[guild].cursor == index:
            play_status = " ❚❚" if Queues[guild].voice_client.is_paused() else " ▶"
            name = play_status + "\t" + (" En pause" if Queues[guild].voice_client.is_paused() else " En cours de lecture")
        else:
            name = "Informations piste"
        embed.set_author(name = name, icon_url = self.bot.user.display_avatar.url)

        # if entry.is_youtube:
        #     if hasattr(entry, 'url'):
        #         embed.video = 
        if hasattr(entry, 'thumbnail'):
            embed.set_image(url = entry.thumbnail)
        #embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text = "Demandé par %s" % entry.applicant.display_name, icon_url = entry.applicant.display_avatar.url)

        return await ctx.respond(embed=embed)
            

    async def queue(self, ctx: discord.ApplicationContext, page:int = None):
        guild = ctx.guild.id
        if guild not in Queues:
            return await ctx.respond('Aucune liste d\'attente', ephemeral=True)

        total_duration = 0
        total_size = 0
        current_playlist = ""
        queue_list = ""
        
        #TODO add this to the config file
        print_size = 20
        print_min, print_max = 0, Queues[guild].size
        
        if page is None:
            print_min = max(Queues[guild].cursor - print_size // 2, 0)
            print_max = min(print_min + print_size, Queues[guild].size)
        else:
            if (page - 1) * print_size > Queues[guild].size or page < 1:
                return await ctx.respond('Index de page invalide', ephemeral=True)
            
            print_min = (page - 1)*print_size
            print_max = min(print_min + print_size, Queues[guild].size)
        
        if print_min == 0:
            queue_list += "==== Début de la file\n"
        else:
            queue_list += "⠀⠀⠀⠀…\n"
            
        for index in range(print_min, print_max):
            entry: Entry = Queues[guild].content[index]
            #Line variables
            tab = ""

            indicator = "\u2003\u2003"
            if Queues[guild].cursor == index:
                if Queues[guild].repeat_mode == "entry":
                    indicator = "\u2002\u2006⟳\u2002"
                else:
                    indicator = "\u2003→\u2004"

            title: str = entry.title
            duration: int = 0
            if hasattr(entry, 'duration'): duration = entry.duration

            total_duration += duration

            # fileSize = ""
            # if hasattr(entry, 'fileSize'): fileSize = entry.fileSize/1000000

            
            
            current_playlist = ""

            #TODO ???
            if entry.playlist is not None:
                tab = "⠀⠀⠀⠀"
                if entry.playlist.id != current_playlist:
                    current_playlist = entry.playlist.id
                    if Queues[guild].repeat_mode == "playlist":
                        queue_list += "⟳ ⠀"
                    else:
                        queue_list += "⠀⠀ "
                    queue_list += f" Playlist : {entry.playlist.title}\n"
                
            
            

            queue_list += f"{tab}{indicator}{index}: {title} - {time_format(duration)}\n"

            
            # totalSize += entry.fileSize


        if print_max == Queues[guild].size:
            queue_list += "==== Fin de la file"
        else:
            queue_list += "⠀⠀⠀⠀…"
        
        repeat_text = {
            "none": "Aucun",
            "entry": "Musique en cours",
            "all": "Tout",
            "playlist": "Playlist"
        }

        embed = discord.Embed(
            description=queue_list,
            color=0x565493
        )
        # | Taille totale : %.2fMo .... , totalSize/1000000
        footerText = "Nombre d'entrées : %d | Mode de répétition : %s\nDurée totale : %s " % (Queues[guild].size, repeat_text[Queues[guild].repeat_mode], time_format(total_duration))
        if page is not None:
            footerText += "\nPage %d/%d" % (page, ((Queues[guild].size - 1) // print_size) + 1)

        if self.bot.user.avatar is None:
            embed.set_author(name = "Liste de lecture")
        else:    
            embed.set_author(name = "Liste de lecture", icon_url = self.bot.user.avatar.url)

        embed.set_footer(text = footerText)

        return await ctx.respond(embed=embed)

    async def move(self, ctx: discord.ApplicationContext, frm: int, to: int):
        guild = ctx.guild.id
        if guild not in Queues:
            return await ctx.respond('Aucune liste d\'attente', ephemeral=True)

        if frm == to:
            return await ctx.respond('La destination ne peut pas être égale à la source', ephemeral=True)

        if frm < Queues[guild].size and frm >= 0 and to < Queues[guild].size and to >= 0:
            title = Queues[guild].get_entry(frm).title
            Queues[guild].move_entry(frm, to)
            return await ctx.respond('%s a été déplacé de %d vers %d' % (title, frm, to))
        else:
            return await ctx.respond('Une des deux positions est invalide', ephemeral=True)

    async def remove(self, ctx: discord.ApplicationContext, idx1: int, idx2: int = None):
        guild = ctx.guild.id
        Queues[guild].voice_client = ctx.voice_client
        if guild not in Queues:
            return await ctx.respond('Aucune liste d\'attente', ephemeral=True)
                    
        if idx1 >= Queues[guild].size or idx1 < 0:
            return await ctx.respond('L\'index 1 (%d) n\'existe pas dans la queue' % (idx1), ephemeral=True)
        
        if idx2 is None: # remove one entry
            entry = Queues[guild].get_entry(idx1)
            if idx1 == Queues[guild].cursor:
                Queues[guild].voice_client.stop()
            Queues[guild].remove_entry(idx1)
            if idx1 <= Queues[guild].cursor:
                Queues[guild].cursor -= 1
            if entry.filename in os.listdir(config.downloadDirectory):
                os.remove(config.downloadDirectory + entry.filename)
            return await ctx.respond('%s a bien été supprimé' % (entry.title))
        else: # remove multiple entries
            oldSize = Queues[guild].size
            if idx2 > oldSize or idx2 < 0:
                return await ctx.respond('L\'index 2 (%d) n\'existe pas dans la queue' % (idx1), ephemeral=True)
            if idx1 > (idx2 - 1):
                return await ctx.respond("Attention à l'ordre des index !", ephemeral=True)
            if idx1 <= Queues[guild].cursor <= idx2 - 1:
                Queues[guild].voice_client.stop()
            for i in range(idx2 - idx1):
                entry = Queues[guild].get_entry(idx1)
                Queues[guild].remove_entry(idx1)
                if idx1 <= Queues[guild].cursor:
                    Queues[guild].cursor -= 1
                if entry.filename in os.listdir(config.downloadDirectory):
                    os.remove(config.downloadDirectory + entry.filename)
            return await ctx.respond("Les entrées commençant à %d jusqu'à %s ont bien été supprimés" % (idx1, "la fin de la liste" if idx2 == oldSize else str(idx2 - 1)))

    async def seek(self, ctx: discord.ApplicationContext, timeCode: str = None):
        guild = ctx.guild.id

        if guild not in Queues:
            return await ctx.respond('Pas de lecture en cours', ephemeral=True)

        currentEntry = Queues[guild].content[Queues[guild].cursor]
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
            Queues[guild].next_entry_condition = NextEntryCondition.SEEK
            Queues[guild].seek_time = desiredStart
            Queues[guild].voice_client.stop()
            return await ctx.respond(f"Utilisation de Seek:tm: !", ephemeral=True) #TODO better response
        else:
            return await ctx.respond("La vidéo sera déjà finie à %s..." % (time_format(desiredStart)), ephemeral=True)

    async def skip(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id

        if guild in Queues:
            if Queues[guild].cursor < Queues[guild].size:
                Queues[guild].next_entry_condition = NextEntryCondition.SKIP
                Queues[guild].repeat_bypass = True
                Queues[guild].cursor = Queues[guild].cursor + 1
                Queues[guild].voice_client.stop()
                return await ctx.respond("Skip")
            else:
                return await ctx.respond('Rien à passer', ephemeral=True)
        else:
            return await ctx.respond('Aucune lecture en cours', ephemeral=True)

    async def pause(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id
        
        if guild in Queues:
            if Queues[guild].voice_client.is_playing():
                Queues[guild].voice_client.pause()
                Queues[guild].pausetime = time.time()
                print(f"[MUSIC.PAUSE] paused listening (GID:{guild})")
                return await ctx.respond("Lecture mise en pause")
            else:
                return await ctx.respond("Lecture déjà en pause !", ephemeral=True)
        else:
            print(f"[MUSIC.PAUSE.ERROR] pause() called but not in the registered guilds (GID:{guild})")
            return await ctx.respond("Selon les informations que je possède, il n'y a aucune lecture en cours sur ce serveur", ephemeral=True)

    async def resume(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id
        if guild in Queues:
            if Queues[guild].voice_client.is_paused():
                Queues[guild].voice_client.resume()
                Queues[guild].starttime = time.time() - (Queues[guild].pausetime - Queues[guild].starttime) # Setting starttime to the correct time to ensure that the time elapsed on the entry is correct when resuming
                Queues[guild].pausetime = 0
                print(f"[MUSIC.RESUME] resumed listening (GID:{guild})")
                return await ctx.respond("Reprise de la lecture")
            else:
                return await ctx.respond("On est déjà en lecture !", ephemeral=True)
        else:
            print(f"[MUSIC.RESUME.ERROR] resume() called but not in the registered guilds (GID:{guild})")
            return await ctx.respond("Selon les informations que je possède, il n'y a aucune lecture en cours sur ce serveur", ephemeral=True)

    async def stop(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id
        
        if Queues[guild].voice_client is not None:
            if Queues[guild].voice_client.is_playing or Queues[guild].voice_client.is_paused:
                if ctx.author.voice is None or ctx.author.voice.channel != Queues[guild].voice_client.channel:
                    return await ctx.respond("Je suis en train de jouer de la musique là, viens me le dire en face !", ephemeral=True)
                Queues[guild].next_entry_condition = NextEntryCondition.STOP
                Queues[guild].repeat_bypass = True
                Queues[guild].voice_client.stop()
                print(f"[MUSIC.STOP] stopped listening (GID:{guild})")
                return await ctx.respond("Ok j'arrête de lire la musique :(")
        else:
            print(f"[MUSIC.STOP.ERROR] stop() called but not in the registered guilds (GID:{guild})")
            return await ctx.respond("Selon les informations que je possède, je suis pas connecté sur ce serveur.", ephemeral=True)

    async def leave(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id

        if guild not in Queues:
            if(ctx.voice_client is not None):
                ctx.voice_client.disconnect()
                return await ctx.respond('Ok bye!')
            else:
                print(f"[MUSIC.LEAVE.ERROR] leave() called but not in the registered guilds (GID:{guild})")
                return await ctx.respond("Selon les informations que je possède, je suis pas connecté sur ce serveur.", ephemeral=True)

        if Queues[guild].voice_client is not None:
            if Queues[guild].voice_client.is_playing() and (ctx.author.voice is None or ctx.author.voice.channel != Queues[guild].voice_client.channel):
                return await ctx.respond("Je suis en train de jouer de la musique là, viens me le dire en face !", ephemeral=True)
            Queues[guild].next_entry_condition = NextEntryCondition.STOP
            Queues[guild].voice_client.stop()
            Queues[guild].voice_client.cleanup()
            await Queues[guild].disconnect()
            for entry in Queues[guild].content:
                if entry.filename in os.listdir(config.downloadDirectory): #TODO implement waiting for process to stop using the file before trying to remove it
                    try:
                        os.remove(config.downloadDirectory + entry.filename) # If running on Windows), the file currently playing will not be erased
                    except:
                        print(f"[MUSIC.LEAVE.ERROR] error while removing file \"{entry.filename}\" (GID:{guild})")
                        continue
            Queues.pop(guild)
            return await ctx.respond('Ok bye!')
        else:
            print(f"[MUSIC.LEAVE.ERROR] leave() called but voice client is None (GID:{guild})")
            return await ctx.respond("Selon les informations que je possède, je suis pas connecté sur ce serveur.", ephemeral=True)

    async def repeat(self, ctx: discord.ApplicationContext, mode: str):
        guild = ctx.guild.id

        if guild not in Queues:
            return await ctx.respond('Aucune liste d\'attente', ephemeral=True)

        repeat_modes = ["none", "entry", "all", "playlist"]
        if mode is not None:
            new_mode = mode
            Queues[guild].repeat_mode = new_mode
        else:
            old_mode = Queues[guild].repeat_mode
            new_mode = repeat_modes[(repeat_modes.index(old_mode) + 1) % len(repeat_modes)]
            Queues[guild].repeat_mode = new_mode

        return await ctx.respond('Le mode de répétition à été changé sur %s' % new_mode)

    async def goto(self, ctx: discord.ApplicationContext, index: int):
        guild = ctx.guild.id
        #print("Goto: [INFO] Invoked by user(%d) in guild(%d)" % (context.author().id, guild))
        if guild not in Queues:
            return await ctx.respond('Aucune liste d\'attente', ephemeral=True)
        if Queues[guild].voice_client is None:
            print("Goto: [ERROR] guild(%d) has no VoiceClient")
            return await ctx.respond('Une erreur est survenue', ephemeral=True)

        if index < Queues[guild].size and index >= 0:
            Queues[guild].cursor = index
            if Queues[guild].voice_client.is_playing() or Queues[guild].voice_client.is_paused():
                Queues[guild].repeat_bypass = True
                Queues[guild].voice_client.stop()
            else:
                await Queues[guild].start_playback()
            return  await ctx.respond(f"Direction la musique n°{index}")
        else:
            return await ctx.respond('L\'index %d n\'existe pas' % index, ephemeral=True)
    



    async def removeGuild(self, id: int):
        if id not in Queues:
            print("RemoveGuild: [NO_ACTION] guild(%d) already removed" % (id))
            return

        if Queues[id].voice_client is None:
            print("RemoveGuild: [REMOVED] guild(%d) had no VoiceClient but is not connected" % (id))
            Queues.pop(id)
            return

        if not Queues[id].voice_client.is_connected():
            Queues.pop(id)
            print("RemoveGuild: [REMOVED] guild(%d) has a VoiceClient but is not connected" % (id))
            return

        if Queues[id].voice_client.is_playing():
            await Queues[id].voice_client.stop()
            print("RemoveGuild: [ACTION] guild(%d) VoiceClient stoped" % (id))
        await asyncio.sleep(0.6)
        
        await Queues[id].voice_client.disconnect()
        print("RemoveGuild: [ACTION] guild(%d) disconnected" % (id))
        

        for entry in Queues[id].content:
            if entry.filename in os.listdir(config.downloadDirectory): #TODO implement waiting for process to stop using the file before trying to remove it
                try:
                    os.remove(config.downloadDirectory + entry.filename) #If running on Windows, the file currently playing is not erased
                except PermissionError :
                    print("RemoveGuild: [EXCEPTION] PermissionError/Not allowed to remove file (%s)" % (config.downloadDirectory + entry.filename))
        print("RemoveGuild: [REMOVED] guild(%d)" % (id))
        Queues.pop(id)





    #afk loop
    @tasks.loop(seconds=VOICE_ACTIVITY_CHECK_DELTA)
    async def music_timeout(self):
        guilds_to_disconnect = []
        
        for guild in Queues.keys():
            if Queues[guild].voice_client is None:
                guilds_to_disconnect.append(guild)
                print(f"Timeout: [INFO] Guild ({guild}) has no voice_client, will be removed")
            else:
                if Queues[guild].is_playing():
                    Queues[guild].voice_activity_update()
                else:
                    if time.time() - Queues[guild].last_voice_activity_time >= config.afkLeaveTime*60:
                        guilds_to_disconnect.append(guild)
                        print(f"Timeout: [INFO] Guild ({guild}) has been inactive for too long, will be removed (AFK time = {time.time() - Queues[guild].last_voice_activity_time} seconds)")
                        
        
        if len(guilds_to_disconnect) > 0:
            for guild_id in guilds_to_disconnect:

                check, file = pick_sound_file("leave")
                if check:
                    if file != "":
                        player = discord.FFmpegPCMAudio(file, options="-vn")
                        Queues[guild_id].voice_client.play(player, after=lambda e: Queues[guild_id].voice_client.loop.create_task(self.removeGuild(guild_id)))
                    else:
                        print("Timeout: No file in Leave folder")
                else:
                    print("PickSound: dossier Sounds inexistant")
                    
                while Queues[guild_id].voice_client.is_playing():
                    await asyncio.sleep(0.1)

                await Queues[guild_id].disconnect()
                await self.removeGuild(guild_id)
                print(f"Guild ({guild}): Disconnected for inactivity")



