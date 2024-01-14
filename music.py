import os
import asyncio
import time
import random

import discord
from discord import VoiceClient, VoiceChannel, TextChannel

from discord.ext import tasks, commands

from youtube import Youtube
from spotify import Spotify
from help import Help
from config import config


activityCheckDelta = 5 #number of seconds between every AFK check

#Guilds = {}

def time_format(seconds: int):
    #if seconds is not None:
        seconds = int(seconds)
        h = seconds // 3600 % 24
        m = seconds % 3600 // 60
        s = seconds % 60
        if h > 0:
            return '{:02d}:{:02d}:{:02d}'.format(h, m, s)
        else:
            return '{:02d}:{:02d}'.format(m, s)
    #return None


class Entry():
    def __init__(self, filename: str, applicant: discord.User, fileSize = 0, playlist = None):
        self.applicant: discord.User = applicant
        self.filename: str = filename
        self.fileSize: int = fileSize
        self.playlist: Playlist = playlist

    def buildMetadataYoutube(self, data):
        self.title = data['title']
        self.channel = data['channel']
        self.channel_url = data['channel_url']
        self.album = data['album'] if 'album' in data else None
        self.duration = data['duration'] if self.fileSize != 0 else 0
        self.thumbnail = data['thumbnail']
        self.id = data['id']
        self.url = data['webpage_url']

    def BuildMetaDataOtherStreams(self, link: str):
        self.title = link
        self.url = link


class Playlist():
    def buildMetadataYoutube(self, data):
        self.title: str = data['title']
        self.uploader = data['uploader'] if 'uploader' in data else None
        self.id = data['id']
        self.url = data['webpage_url']

    def buildMetadataSpotify(self, data):
        pass


class Queue():
    def __init__(self, voice_client: VoiceClient, text_channel: TextChannel):
        self.content: list[Entry] = []
        self.size = 0
        self.cursor = 0
        self.starttime = 0
        self.pausetime = 0
        self.lastVoiceActivityTime = time.time()
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.repeat_mode = "none"  # none, entry, playlist, all
        self.repeat_bypass = False
        self.seekTime = -1
        self.isOtherSource: bool = False

    #Voice Channel
    def getVoiceChannel(self) -> VoiceChannel:
        return self.voice_client.channel

    #Voice Client
    def isConnected(self) -> bool:
        return self.voice_client.is_connected()

    def isPlaying(self) -> bool:
        return self.voice_client.is_playing()

    def Stop(self) -> None:
        self.voice_client.stop()

    async def connect(self, voiceChannel: VoiceChannel) -> None:
        self.voice_client = await voiceChannel.connect(timeout=600, reconnect=True)
        
    async def reconnect(self) -> None:
        self.voice_client = await self.voice_client.channel.connect(timeout=600, reconnect=True)

    async def move(self, newVoiceChannel: VoiceChannel) -> None:
        await self.voice_client.move_to(newVoiceChannel)

    async def disconnect(self) -> None:
        await self.voice_client.disconnect()

    def voiceActivityUpdate(self) -> None:
        self.lastVoiceActivityTime = time.time()

    #Text Channel
    def checkTextChannel(self, textChannel: TextChannel) -> bool: #preventing typing commands in other text channels
        return self.text_channel == textChannel

    def moveTextChannel(self, newTextChannel: TextChannel) -> None: #change listening text channel
        self.text_channel = newTextChannel


    #Playback
    async def startPlayback(self, timestart: int = 0, supressOutput: bool = False):
        if self.voice_client.is_connected() and not self.voice_client.is_playing():
            entry: Entry = self.content[self.cursor]
            filename: str = config.downloadDirectory + entry.filename if entry.fileSize != 0 else entry.filename
            #seek parameters
            before: str = ""
            if timestart > 0:
                before = "-ss %d" % (timestart)
            else:
                timestart = 0

            player: discord.FFmpegPCMAudio = discord.FFmpegPCMAudio(filename, before_options = before, options = "-vn")
            self.voice_client.play(player, after=lambda e: self.nextEntry())
            self.starttime = time.time() - timestart

            if not supressOutput:
                if timestart > 0:
                    await self.text_channel.send('Déplacement du pointeur à **[%s]** dans la lecture en cours : %s' % (time_format(timestart), entry.title))
                else:
                    await self.text_channel.send('Maintenant en lecture : %s' % (entry.title))

    def nextEntry(self):
        if self.repeat_bypass is False:
            if self.repeat_mode == "none":
                self.cursor = self.cursor + 1
            elif self.repeat_mode == "entry":
                pass
            elif self.repeat_mode == "all":
                if self.cursor == self.size - 1:
                    self.cursor = 0
                else:
                    self.cursor = self.cursor + 1
            elif self.repeat_mode == "playlist":
                def gotostart():
                    i = self.cursor-1
                    while self.content[i].playlist is not None and i >= 0:
                        if self.content[i].playlist.id == current_entry.playlist.id:
                            i = i-1
                        else:
                            break
                    self.cursor = i

                current_entry = self.content[self.cursor]
                if current_entry.playlist.id is not None:
                    if self.cursor < self.size-1:
                        if self.content[self.cursor+1].playlist is not None:
                            if self.content[self.cursor+1].playlist.id != current_entry.playlist.id:
                                gotostart()
                        else:
                            gotostart()
                    elif self.cursor == self.size - 1:
                        gotostart()

                self.cursor = self.cursor + 1
        
        noOutput: bool = False
        startingTime: int = 0
        if self.seekTime >= 0 and self.repeat_bypass is True:
            #noOutput = True
            startingTime = self.seekTime
            print("seeking entry at %d seconds" % (self.seekTime))
        else:
            print("next entry")

        self.seekTime = -1
        self.repeat_bypass = False
        if self.cursor < self.size:
            coro = self.startPlayback(timestart = startingTime, supressOutput = noOutput)
            fut = asyncio.run_coroutine_threadsafe(coro, self.voice_client.loop)
            try:
                fut.result()
            except:
                print("coro error")

    def PlayOther(self):
        if(self.isPlaying):
            self.isOtherSource = True
        pass

    async def addEntry(self, entry: Entry, position=None) -> int:
        if position is None or position == self.size:
            self.content.append(entry)
        else:
            self.content.insert(position, entry)
        self.size = self.size + 1
        if self.size == self.cursor + 1:
            await self.startPlayback()

        return position or self.size-1

    def removeEntry(self, index: int):
        self.content.pop(index)
        self.size = self.size - 1

    def moveEntry(self, frm: int, to: int):
        entry = self.content[frm]
        self.content.pop(frm)
        self.content.insert(to, entry)

    def getIndex(self, entry: Entry) -> int:
        return self.content.index(entry)

    def getEntry(self, index: int) -> Entry:
        return self.content[index]





Queues: 'dict[int, Queue]' = {}




class Music():
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        if config.afkLeaveActive:
            self.musicTimeout.start()

    async def play(self, ctx: discord.ApplicationContext, query: str):
        await ctx.defer(ephemeral=True)

        authorVoice = ctx.author.voice
        if authorVoice is None: # Not connected
            return await ctx.respond("Vous n'êtes pas connectés à un salon vocal", ephemeral=True)
        
        guild = ctx.guild.id
        authorText = ctx.channel

        if guild not in Queues: #New Guild
            Queues[guild] = Queue(None, authorText)
            Queues[guild].voice_client = await authorVoice.channel.connect(timeout=600, reconnect=True)

            print("Guild (%d): new connection to channel %s" % (guild, authorVoice.channel.name))

            #Only add the startup sound if there is no queue
            check, file = pickSoundFile("Startup")
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
                    await queue.addEntry(entry)
                    #print("added to queue")
                else:
                    print("Aucun fichier trouvé pour le startup")
            else:
                print("dossier Sounds inexistant")
        else: #Existing queue checks
            if not Queues[guild].voice_client.is_connected():
                print("Voice client is none")
                await Queues[guild].connect(authorVoice.channel)
                if Queues[guild].voice_client.is_connected():
                    print("Voice client is reconnected")
                else:
                    print("Voice client was unable to reconnect")
                    Queues.pop(guild)
                    return await ctx.respond("Je n'ai pas réussi à me reconnecter...", ephemeral=True)
                    

            if authorVoice.channel != Queues[guild].voice_client.channel:
                await Queues[guild].move(authorVoice.channel)

                print("Guild (%d): moved to %s" % (guild, authorVoice.channel))
        # print("Guild (%d): Connected to %s (number of members: %d)" % (guild, Queues[guild].voice_client.channel.name, len(Queues[guild].voice_client.channel.members)))

        queue = Queues[guild]
        entry = None

        if query.startswith("www."): #Append HTTPS to the link sent
            query = "https://" + query

        
        if query.startswith(("spotify:", "https://open.spotify.com/")): #Spotify research
            if not config.spotifyEnabled:
                return await ctx.respond('La recherche Spotify n\'a pas été configurée')
            
            if query.startswith("https://open.spotify.com/"):
                query = query[len("https://open.spotify.com/"):].replace('/', ':')
            else:
                query = query[len("spotify:"):]

            try:
                if(len(query.split(':')) == 2):
                    [_type, _id] = query.split(':')
                else:
                    [_misc, _type, _id] = query.split(':')

                if _type == 'track':
                    track = Spotify.getTrack(_id)
                    query = "%s %s" % (track['name'], track['artists'][0]['name'])
                elif _type == 'playlist':
                    return await ctx.respond('Les playlists Spotify ne sont pas pris en charge', ephemeral=True)
            except:
                return await ctx.respond('Le lien n\'est pas valide', ephemeral=True)

        # Other streams
        if (query.startswith("http") or query.startswith("udp://")) and not query.startswith(("https://youtu.be", "https://www.youtube.com", "https://youtube.com")):
            entry = Entry(query, ctx.author)
            entry.BuildMetaDataOtherStreams(query)
            position = await queue.addEntry(entry)
            return await ctx.respond("%d: %s a été ajouté à la file d\'attente" % (position, query), ephemeral=True)
        else: #YouTube Search
            if not query.startswith("https://"):
                message: discord.WebhookMessage = await ctx.respond("Recherche de \"%s\"..." % query, ephemeral=True)
                try:
                    result = await Youtube.searchVideos(query)
                except:
                    return await message.edit(content='Aucune musique trouvé')
                url = result["link"]
                # print(url)
            else:
                message: discord.WebhookMessage = await ctx.respond("Investigation sur \"%s\"..." % query[8:], ephemeral=True)
                url = query

            try:
                data = await Youtube.fetchData(url, self.bot.loop)
                print(data['webpage_url'])
            except:
                return await message.edit('Le lien n\'est pas valide')

            applicant = ctx.author
            if 'entries' in data:
                playlist = Playlist()
                playlist.buildMetadataYoutube(data)
                queue_start = Queues[guild].size
                for i in range(len(data['entries'])):
                    if data['entries'][i] is not None:
                        if data['entries'][i]['is_live'] == True:
                            filename = data['entries'][i]['url']
                            fileSize = 0
                        else:
                            try:
                                filename = Youtube.getFilename(data['entries'][i])
                                text = "(%d/%d) Téléchargement de %s..." % (i+1, len(data['entries']), data['entries'][i]['title']) 
                                await Youtube.downloadAudio(data['entries'][i]['webpage_url'], message, text, self.bot.loop),
                            except:
                                await message.edit(content="Erreur lors du téléchargement de %s" % data['entries'][i]['title'])
                                continue
                            fileSize = os.path.getsize(config.downloadDirectory + filename)

                        if Queues[guild].voice_client.is_connected():
                            entry = Entry(filename, applicant, fileSize, playlist)
                            entry.buildMetadataYoutube(data['entries'][i])
                            position = await queue.addEntry(entry, queue_start + i) #TODO bug when stopping the bot while a playlist is currently added in the queue, the bot will resume by itself by adding the next track to the queue
                            if i == len(data['entries']) - 1:
                                await message.edit(content="%s a été ajouté à la file d\'attente" % data['title'])
                            else:
                                await message.edit(content="(%d/%d) %d: %s a été ajouté à la file d\'attente" % (i+1, len(data['entries']), position, data['entries'][i]['title']))
                        else:
                            await message.edit(content="Téléchargement annulé")
                            break
            else:
                if data['is_live'] == True:
                    filename = data['url']
                    fileSize = 0
                else:
                    try:
                        filename = Youtube.getFilename(data)
                        text = "Téléchargement de %s..." % data['title']
                        await Youtube.downloadAudio(data['webpage_url'], message, text, self.bot.loop)
                        fileSize = os.path.getsize(config.downloadDirectory + filename)
                    except:
                        return await message.edit(content="Erreur lors du téléchargement de %s" % data['title'])
                    

                if Queues[guild].voice_client.is_connected():
                    entry = Entry(filename, applicant, fileSize)
                    entry.buildMetadataYoutube(data)
                    position = await queue.addEntry(entry)
                    await message.edit(content="%d: %s a été ajouté à la file d\'attente" % (position, data['title']))
                    await ctx.send(f"{ctx.author.display_name} a ajouté une musique…")
                else:
                    print("not connected")

    async def nowplaying(self, ctx: discord.ApplicationContext):
        guild = ctx.guild.id
        if guild not in Queues or Queues[guild].cursor == Queues[guild].size:
            return await ctx.respond('Rien en lecture', ephemeral=True)
        else:
            await self.info(ctx, Queues[guild].cursor)

    async def info(self, ctx: discord.ApplicationContext, index: int):
        guild = ctx.guild.id
        if guild not in Queues:
            return await ctx.respond('Aucune liste d\'attente', ephemeral=True)

        #Queues[guild].voice_client = ctx.voice_client
        
        if index >= Queues[guild].size and index < 0:
            return await ctx.respond('L\'index %d n\'existe pas' % (index), ephemeral=True)
        else:
            entry = Queues[guild].content[index]
            content = ""
            if hasattr(entry, 'channel') and hasattr(entry, 'channel_url'): content += "Chaîne : [%s](%s)\n" % (entry.channel, entry.channel_url)

            if Queues[guild].cursor == index:
                pause: str = "[Paused]" if Queues[guild].voice_client.is_paused() else ""
                current: float = Queues[guild].pausetime - Queues[guild].starttime if Queues[guild].voice_client.is_paused() else time.time() - Queues[guild].starttime
                
                if not hasattr(entry, 'duration'): #Other Stream
                    content += "Durée d'écoute : %s %s\n" % (time_format(current), pause)
                else: #File
                    content += "Progression : %s/%s %s\n" % (time_format(current), time_format(entry.duration), pause)
                    
                    #Progress bar
                    progress = (current/entry.duration)*20
                    content += "["
                    for i in range(0,20):
                        if int(progress) == i: content += "●"
                        else: content += "─"
                    content += "] (%s%s)\n" % (int((current/entry.duration)*100),'%')

            if hasattr(entry, 'album'): content += "Album : %s\n" % (entry.album)
            if hasattr(entry, 'playlist'):
                if entry.playlist is not None : content += "Playlist : [%s](%s)\n" % (entry.playlist.title, entry.playlist.url)
            content += "Position : %d" % index

            embed = discord.Embed(
                title = entry.title,
                url = entry.url,
                description = content,
                color = 0x565493
            )

            if Queues[guild].cursor == index:
                bigPause = "❚❚" if Queues[guild].voice_client.is_paused() else "▶"
                name = bigPause + "\t" + (" En pause" if Queues[guild].voice_client.is_paused() else " En cours de lecture")
            else:
                name = "Informations piste"
            embed.set_author(name = name, icon_url = self.bot.user.display_avatar.url)
            if hasattr(entry, 'thumbnail'): embed.set_image(url = entry.thumbnail)
            #embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text = "Demandé par %s" % entry.applicant.display_name, icon_url = entry.applicant.display_avatar.url)

            return await ctx.respond(embed=embed)
            

    async def queue(self, ctx: discord.ApplicationContext, page:int = None):
        guild = ctx.guild.id
        if guild not in Queues:
            return await ctx.respond('Aucune liste d\'attente', ephemeral=True)

        totalDuration = 0
        totalSize = 0
        current_playlist = ""
        list = ""
        
        #TODO add this to the config file
        printSize = 20
        printMin, printMax = 0, Queues[guild].size
        
        if page is None:
            printMin = max(Queues[guild].cursor - printSize // 2, 0)
            printMax = min(printMin + printSize, Queues[guild].size)
        else:
            if (page - 1) * printSize > Queues[guild].size or page < 1:
                return await ctx.respond('Index de page invalide', ephemeral=True)
            
            printMin = (page - 1)*printSize
            printMax = min(printMin + printSize, Queues[guild].size)
        
        if printMin == 0:
            list += "==== Début de la file\n"
        else:
            list += "⠀⠀⠀⠀…\n"
            
        for index in range(printMin, printMax):
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

            totalDuration += duration

            # fileSize = ""
            # if hasattr(entry, 'fileSize'): fileSize = entry.fileSize/1000000

            
            
            current_playlist = ""

            #TODO ???
            if entry.playlist is not None:
                tab = "⠀⠀⠀⠀"
                if entry.playlist.id != current_playlist:
                    current_playlist = entry.playlist.id
                    if Queues[guild].repeat_mode == "playlist":
                        list += "⟳ ⠀"
                    else:
                        list += "⠀⠀ "
                    list += " Playlist : %s\n" % entry.playlist.title
                
            
            

            list += "%s%s%d: %s - %s\n" % (tab, indicator, index, title, time_format(duration))

            
            # totalSize += entry.fileSize


        if printMax == Queues[guild].size:
            list += "==== Fin de la file"
        else:
            list += "⠀⠀⠀⠀…"
        
        repeat_text = {
            "none": "Aucun",
            "entry": "Musique en cours",
            "all": "Tout",
            "playlist": "Playlist"
        }

        embed = discord.Embed(
            description=list,
            color=0x565493
        )
        # | Taille totale : %.2fMo .... , totalSize/1000000
        footerText = "Nombre d'entrées : %d | Mode de répétition : %s\nDurée totale : %s " % (Queues[guild].size, repeat_text[Queues[guild].repeat_mode], time_format(totalDuration))
        if page is not None:
            footerText += "\nPage %d/%d" % (page, ((Queues[guild].size - 1) // printSize) + 1)

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
            title = Queues[guild].getEntry(frm).title
            Queues[guild].moveEntry(frm, to)
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
            entry = Queues[guild].getEntry(idx1)
            if idx1 == Queues[guild].cursor:
                Queues[guild].voice_client.stop()
            Queues[guild].removeEntry(idx1)
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
                entry = Queues[guild].getEntry(idx1)
                Queues[guild].removeEntry(idx1)
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
            Queues[guild].seekTime = desiredStart
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
                await Queues[guild].startPlayback()
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
    @tasks.loop(seconds=activityCheckDelta)
    async def musicTimeout(self):
        GuildsToDisconnect = []
        
        for guild in Queues.keys():
            if Queues[guild].voice_client is None:
                GuildsToDisconnect.append(guild)
                print("Timeout: [INFO] Guild (%d) has no voice_client, will be removed" % (guild))
            else:
                if Queues[guild].isPlaying():
                    Queues[guild].voiceActivityUpdate()
                else:
                    if time.time() - Queues[guild].lastVoiceActivityTime >= config.afkLeaveTime*60:
                        GuildsToDisconnect.append(guild)
                        print("Timeout: [INFO] Guild (%d) has been inactive for too long, will be removed (AFK time = %d seconds)" % (guild, time.time() - Queues[guild].lastVoiceActivityTime))
                        
        
        if len(GuildsToDisconnect) > 0:
            for id in GuildsToDisconnect:

                check, file = pickSoundFile("Leave")
                if check:
                    if file != "":
                        player = discord.FFmpegPCMAudio(file, options="-vn")
                        Queues[id].voice_client.play(player, after=lambda e: Queues[id].voice_client.loop.create_task(self.removeGuild(id)))
                    else:
                        print("Timeout: No file in Leave folder")
                else:
                    print("PickSound: dossier Sounds inexistant")
                    
                while Queues[id].voice_client.is_playing():
                    await asyncio.sleep(0.1)

                await Queues[id].disconnect()
                await self.removeGuild(id)
                print(("Guild (%d): Disconnected for inactivity" % (guild)))


def pickSoundFile(folderName: str) -> tuple[bool, str]:
    fPath = config.soundDirectory + folderName
    if os.path.isdir(fPath):
        if len(os.listdir(fPath)) > 0:
            rnd = random.randint(0, len(os.listdir(fPath))-1)
            return True, "%s/%s" % (fPath, os.listdir(fPath)[rnd])
        else:
            return True, "" # Folder exist but no file found
    else: 
        return False, "" # Folder does not exist

