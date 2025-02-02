import os
import asyncio
import time
import random
import traceback



import discord
from discord.ext import tasks, commands



from DJscordBot.entities import Entry, Playlist, Queue
from DJscordBot.utils import time_format
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

        author_voice = ctx.author.voice
        if author_voice is None: # Not connected
            return await ctx.respond(
                "Vous n'êtes pas connectés à un salon vocal", 
                phemeral=True)
        
        guild = ctx.guild.id
        author_text = ctx.channel

        #New Guild
        if guild not in Queues: 
            Queues[guild] = Queue(None, author_text)
            Queues[guild].voice_client = await author_voice.channel.connect(
                timeout=600,
                reconnect=True)

            print(f"Guild ({guild}): new connection to channel {author_voice.channel.name}")

            #Only add the startup sound if there is no queue
            check, file = pick_sound_file("Startup")
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

                    queue = Queues[guild]
                    await queue.add_entry(entry)
                    #print("added to queue")
                else:
                    print("[INFO] Music.play(): Startup: Aucun fichier trouvé")
            else:
                print("[INFO] Music.play(): Startup: Dossier Sounds inexistant")
        #Existing queue checks
        else: 
            if not Queues[guild].voice_client.is_connected():
                print("Voice client is none")
                await Queues[guild].connect(author_voice.channel)
                if Queues[guild].voice_client.is_connected():
                    print("Voice client is reconnected")
                else:
                    print("Voice client was unable to reconnect")
                    Queues.pop(guild)
                    return await ctx.respond(
                        "Je n'ai pas réussi à me reconnecter...",
                        ephemeral=True)
                    

            if author_voice.channel != Queues[guild].voice_client.channel:
                await Queues[guild].move(author_voice.channel)

                print(f"Guild ({guild}): moved to {author_voice.channel}")
        
        # print("Guild (%d): Connected to %s (number of members: %d)" % (guild, Queues[guild].voice_client.channel.name, len(Queues[guild].voice_client.channel.members)))

        queue = Queues[guild]
        entry = None



        # Query processing

        # Append HTTPS to the link sent
        if query.startswith("www."):
            query = "https://" + query


        # Spotify Search
        if query.startswith(("spotify:", "https://open.spotify.com/")): 
            if not config.spotifyEnabled:
                return await ctx.respond('La recherche Spotify n\'a pas été configurée')
            
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
                elif _type == 'playlist':
                    return await ctx.respond('Les playlists Spotify ne sont pas pris en charge', ephemeral=True)
                else:
                    raise Exception("Unhandled type")
            except Exception:
                print(f"[FAILED SEARCH] Spotify search failed to find music\n\n{traceback.format_exc()}")
                return await ctx.respond('Le lien Spotify est invalide', ephemeral=True)

        
        # Other streams
        if (query.startswith("http") or query.startswith("udp://")) and not query.startswith(("https://youtu.be", "https://www.youtube.com", "https://youtube.com")):
            entry = Entry(query, ctx.author)
            entry.BuildMetaDataOtherStreams(query)
            position = await queue.add_entry(entry)
            return await ctx.respond(
                f"{position}: {query} a été ajouté à la file d\'attente",
                ephemeral=True)
        
        
        # YouTube Search
        else:
            # Search query
            if not query.startswith("https://"):
                message: discord.WebhookMessage = await ctx.respond(
                    f"Recherche de \"{query}\"...",
                    ephemeral=True)
                found: bool = False
                result = None
                # Méthode youtube-search-python
                try:
                    result = await Youtube.searchVideos_YSP(query)
                    if result is not None:
                        found = True
                except Exception:
                    print("[FAILED SEARCH] ysp.Search failed to find music, falling back to yt-dlp")
                    # print(f"[FAILED SEARCH] ysp.Search failed to find music\n\n{traceback.format_exc()}")
                if not found:
                    try:
                        result = await Youtube.searchVideosYT_DLP(query)
                        if result is not None:
                            found = True
                    except Exception:
                        print(f"[FAILED SEARCH] yt-dlp.Search failed to find music\n\n{traceback.format_exc()}")

                if not found:
                    return await message.edit(content="La recherche à échoué")
                await message.edit(content=f"Vidéo trouvée : **{(result['title'])}**")

                # url = result["webpage_url"]
                # print(url)
            # Youtube Link
            else:
                message: discord.WebhookMessage = await ctx.respond(
                    f"Investigation sur \"{query[8:]}\"...",
                    ephemeral=True)
                result = await Youtube.searchVideosYT_DLP(query)


            #TODO qu'est-ce que c'est que ce truc ?
            try:
                # data = await Youtube.fetchData(url, self.bot.loop)
                data = result
                print(result['webpage_url'])
            except Exception:
                print(f"[FAILED SEARCH] link check failed\n\n{traceback.format_exc()}")
                return await message.edit('Une erreur est survenue lors de la vérification du lien')

            applicant = ctx.author

            if 'entries' in data:
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
                                print(f"[FAILED DOWNLOAD] unable to download {data['entries'][i]['title']}\n\n{traceback.format_exc()}")
                                await message.edit(content=f"Erreur lors du téléchargement de {data['entries'][i]['title']}")
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
                        print(f"[FAILED DOWNLOAD] unable to download {data['entries'][i]['title']}\n\n{traceback.format_exc()}")
                        return await message.edit(content=f"Erreur lors du téléchargement de {data['title']}")
                    

                if Queues[guild].voice_client.is_connected():
                    entry = Entry(filename, applicant, file_size)
                    entry.buildMetadataYoutube(data)
                    position = await queue.add_entry(entry)
                    await message.edit(content=f"{position}: {data['title']} a été ajouté à la file d\'attente")
                    await ctx.send(f"{ctx.author.display_name} a ajouté une musique…")
                else:
                    print("Trying to add music but voice_client is not connected")

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
        if hasattr(entry, 'channel') and hasattr(entry, 'channel_url'):
            content += f"Chaîne : [{entry.channel}]({entry.channel_url})\n"

        if Queues[guild].cursor == index:
            pause: str = "[Paused]" if Queues[guild].voice_client.is_paused() else ""
            current: float = Queues[guild].pausetime - Queues[guild].starttime if Queues[guild].voice_client.is_paused() else time.time() - Queues[guild].starttime
            
            if not hasattr(entry, 'duration'): #Other Stream
                content += f"Durée d'écoute : {time_format(current)} {pause}\n"
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
                content += f"] ({int((current/entry.duration)*100)}%)\n"

        if hasattr(entry, 'album'):
            content += f"Album : {entry.album}\n"
        if hasattr(entry, 'playlist'):
            if entry.playlist is not None :
                content += f"Playlist : [{entry.playlist.title}]({entry.playlist.url})\n"
        content += f"Position : {index}"

        embed = discord.Embed(
            title = entry.title,
            url = entry.url,
            description = content,
            color = 0x565493
        )

        if Queues[guild].cursor == index:
            big_pause = "❚❚" if Queues[guild].voice_client.is_paused() else "▶"
            name = big_pause + "\t" + (" En pause" if Queues[guild].voice_client.is_paused() else " En cours de lecture")
        else:
            name = "Informations piste"
        embed.set_author(name = name, icon_url = self.bot.user.display_avatar.url)

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
            return await ctx.respond("Quelque chose ne va pas dans la syntaxe (doit être hh:mm:ss ou mmmm:ss ou bien ssss)", ephemeral=True)
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
            Queues[guild].repeat_bypass = True
            Queues[guild].seek_time = desiredStart
            Queues[guild].voice_client.stop()
            return await ctx.respond(f"Utilisation de seek !") #TODO better response
        else:
            return await ctx.respond("La vidéo sera déjà finie à %s..." % (time_format(desiredStart)), ephemeral=True)

    async def skip(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id

        if guild in Queues:
            if Queues[guild].cursor < Queues[guild].size:
                Queues[guild].repeat_bypass = True
                Queues[guild].cursor = Queues[guild].cursor + 1
                Queues[guild].voice_client.stop()
                return await ctx.respond("Skip")
            else:
                return await ctx.respond('Rien à passer', ephemeral=True)
        else:
            return await ctx.respond('Aucune lecture en cours', ephemeral=True)

    #TODO
    async def pause(self, context: commands.Context):
        guild = context.guild.id
        
        if guild in Queues:
            if Queues[guild].voice_client.is_playing():
                Queues[guild].voice_client.pause()
                Queues[guild].pausetime = time.time()
                return await context.send('Mis en pause')
            else:
                return await context.send('Déjà en pause')
        else:
            return await context.send('Aucune lecture en cours sur ce serveur')

    #TODO
    async def resume(self, context: commands.Context):
        guild = context.guild.id
        if guild in Queues:
            if Queues[guild].voice_client.is_paused():
                Queues[guild].voice_client.resume()
                Queues[guild].starttime = time.time() - (Queues[guild].pausetime - Queues[guild].starttime) # Setting starttime to the correct time to ensure that the time elapsed on the entry is correct when resuming
                Queues[guild].pausetime = 0
                return await context.send('Reprise de la lecture')
            else:
                return await context.send('Déjà en lecture')
        else:
            return await context.send('Aucune lecture en cours sur ce serveur')

    async def stop(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id
        
        if Queues[guild].voice_client is not None:
            if Queues[guild].voice_client.is_playing or Queues[guild].voice_client.is_paused:
                if ctx.author.voice is None or ctx.author.voice.channel != Queues[guild].voice_client.channel:
                    return await ctx.respond("Je suis en train de jouer de la musique là, viens me le dire en face !", ephemeral=True)
                Queues[guild].repeat_bypass = True
                Queues[guild].voice_client.stop()
                return await ctx.respond("Ok j'arrête de lire la musique :(")
        else:
            return await ctx.respond("Je suis pas connecté sur ce serveur en fait !", ephemeral=True)

    async def leave(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id

        if guild not in Queues:
            if(ctx.voice_client is not None):
                ctx.voice_client.disconnect()
                return await ctx.respond('Ok bye!')
            else:
                return await ctx.respond('Aucune liste d\'attente', ephemeral=True)

        if Queues[guild].voice_client is not None:
            if Queues[guild].voice_client.is_playing() and (ctx.author.voice is None or ctx.author.voice.channel != Queues[guild].voice_client.channel):
                return await ctx.respond("Je suis en train de jouer de la musique là, viens me le dire en face !")
            Queues[guild].voice_client.stop()
            Queues[guild].voice_client.cleanup()
            await Queues[guild].disconnect()
            for entry in Queues[guild].content:
                if entry.filename in os.listdir(config.downloadDirectory): #TODO implement waiting for process to stop using the file before trying to remove it
                        try:
                            os.remove(config.downloadDirectory + entry.filename) # If running on Windows), the file currently playing will not be erased
                        except:
                            print("Leave: error remove")
            Queues.pop(guild)
            return await ctx.respond('Ok bye!')
        else:
            return await ctx.respond('Je suis pas connecté en fait !')

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

                check, file = pick_sound_file("Leave")
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



