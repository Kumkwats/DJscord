import asyncio
from audioop import reverse
import os
import discord
from discord.ext import commands,tasks
from youtube import Youtube
from spotify import Spotify
from help import Help
from config import config
import time
import random

activityCheckDelta = 5 #number of seconds between every AFK check

Queues = {}

def time_format(seconds):
    if seconds is not None:
        seconds = int(seconds)
        h = seconds // 3600 % 24
        m = seconds % 3600 // 60
        s = seconds % 60
        if h > 0:
            return '{:02d}:{:02d}:{:02d}'.format(h, m, s)
        else:
            return '{:02d}:{:02d}'.format(m, s)
    return None


class Entry():
    def __init__(self, filename, applicant, fileSize=0, playlist=None):
        self.applicant = applicant
        self.filename = filename
        self.fileSize = fileSize
        self.playlist = playlist

    def buildMetadataYoutube(self, data):
        self.title = data['title']
        self.channel = data['channel']
        self.channel_url = data['channel_url']
        self.album = data['album'] if 'album' in data else None
        self.duration = data['duration'] if self.fileSize != 0 else 0
        self.thumbnail = data['thumbnail']
        self.id = data['id']
        self.url = data['webpage_url']


class Playlist():
    def buildMetadataYoutube(self, data):
        self.title = data['title']
        self.uploader = data['uploader'] if 'uploader' in data else None
        self.id = data['id']
        self.url = data['webpage_url']

    def buildMetadataSpotify(self, data):
        pass


class Queue():
    def __init__(self, voice_client, text_channel, repeat_mode="none"):
        self.content = []
        self.size = 0
        self.cursor = 0
        self.starttime = 0
        self.pausetime = 0
        self.lastVoiceActivityTime = time.time()
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.repeat_mode = repeat_mode  # none, entry, playlist, all
        self.repeat_bypass = False
        self.seekTime = -1

        #self.time = 0 #timeout
        

    #Voice Channel
    def getVoiceChannel(self):
        return self.voice_client.channel

    #Voice Client
    def isConnected(self):
        return self.voice_client.is_connected()

    def isPlaying(self):
        return self.voice_client.is_playing()

    async def connect(self, voiceChannel):
        self.voice_client = await voiceChannel.connect(timeout=600, reconnect=True)
        
    async def reconnect(self):
        self.voice_client = await self.voice_client.channel.connect(timeout=600, reconnect=True)

    async def move(self, newVoiceChannel):
        await self.voice_client.move_to(newVoiceChannel)

    async def disconnect(self):
        await self.voice_client.disconnect()

    def voiceActivityUpdate(self):
        self.lastVoiceActivityTime = time.time()

    #Text Channel
    def checkTextChannel(self, textChannel): #preventing typing commands in other text channels
        return self.text_channel == textChannel

    def moveTextChannel(self, newTextChannel): #change listening text channel
        self.text_channel = newTextChannel


    #Playback
    async def startPlayback(self, timestart = 0, supressOutput = False):
        if self.voice_client.is_connected() and not self.voice_client.is_playing():
            entry = self.content[self.cursor]
            filename = config.downloadDirectory + entry.filename if entry.fileSize != 0 else entry.filename
            #seek parameters
            before = ""
            if timestart > 0:
                before = "-ss %d" % (timestart)
            else:
                timestart = 0

            player = discord.FFmpegPCMAudio(filename, before_options = before, options = "-vn")
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
        
        noOutput = False
        startingTime = 0
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

    async def addEntry(self, entry, position=None):
        if position is None or position == self.size:
            self.content.append(entry)
        else:
            self.content.insert(position, entry)
        self.size = self.size + 1
        if self.size == self.cursor + 1:
            await self.startPlayback()

        return position or self.size-1

    def removeEntry(self, index):
        self.content.pop(index)
        self.size = self.size - 1

    def moveEntry(self, frm, to):
        entry = self.content[frm]
        self.content.pop(frm)
        self.content.insert(to, entry)

    def getIndex(self, entry):
        return self.content.index(entry)

    def getEntry(self, index):
        return self.content[index]


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if config.afkLeaveActive:
            self.musicTimeout.start()

    @commands.command(aliases=['p', 'lire', 'jouer'])
    async def play(self, context, *, query: str = None):
        if query is None:
            return await context.send(embed=Help.get(context, 'music', 'play'))

        authorVoice = context.author.voice
        #Queues[guild].voice_client = context.voice_client
        authorText = context.channel

        guild = context.guild.id


        if authorVoice is None:
            return await context.send("Vous n'êtes pas connectés à un salon vocal")
        else:
            if guild not in Queues:
                print("Guild (%d): new connection to channel%s" % (guild, authorVoice.channel))
                Queues[guild] = Queue(None, authorText)
                Queues[guild].voice_client = await authorVoice.channel.connect(timeout=600, reconnect=True)
                #Queues[guild] = Queue(Queues[guild].voice_client, authorText)

                #Only add the startup sound if there is no queue
                check, file = pickSoundFile("Startup")
                if check:
                    if file != "":
                        entry = Entry(file, context.author)
                        entry.title = "Booting up..."
                        entry.channel = "DJPatrice"
                        entry.channel_url = "https://github.com/Kumkwats/my-discord-bot"
                        entry.duration = 0
                        entry.album = None
                        entry.thumbnail = "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/3ddaa372-c58c-4587-911e-1d625dff64dc/dapv26n-b138c16c-1cfc-45c3-9989-26fcd75d3060.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3sicGF0aCI6IlwvZlwvM2RkYWEzNzItYzU4Yy00NTg3LTkxMWUtMWQ2MjVkZmY2NGRjXC9kYXB2MjZuLWIxMzhjMTZjLTFjZmMtNDVjMy05OTg5LTI2ZmNkNzVkMzA2MC5qcGcifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6ZmlsZS5kb3dubG9hZCJdfQ.PnU42OFMHcio7nJ4a5Jsp8C-d6exHqd3vInU1682x1E"
                        entry.url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

                        queue = Queues[guild]
                        await queue.addEntry(entry)
                    else:
                        print("Aucun fichier trouvé pour le startup")
                else:
                    print("dossier Sounds inexistant")
            else:
                if not Queues[guild].voice_client.is_connected():
                    print("Voice client is none")
                    await Queues[guild].connect(authorVoice.channel)
                    if Queues[guild].voice_client.is_connected():
                        print("Voice client is reconnected")
                    else:
                        print("Voice client was unable to reconnect")
                        Queues.pop(guild)
                        return await context.send("Je n'ai pas réussi à me reconnecter...")
                        

                        
                if authorVoice.channel != Queues[guild].voice_client.channel:
                    await Queues[guild].move(authorVoice.channel)
                    # print("Guild (%d): moved to %s" % (guild, authorVoice.channel))
            # print("Guild (%d): Connected to %s (number of members: %d)" % (guild, Queues[guild].voice_client.channel.name, len(Queues[guild].voice_client.channel.members)))

        queue = Queues[guild]
        entry = None

        if query.startswith("www."):
            query = "https://" + query
            if context.author.id == 289086025442000896:
                await context.send("Mael t'abuse à mettre des liens en www, mais j'accepte quand même")

        if query.startswith(("spotify:", "https://open.spotify.com/")):
            if not config.spotifyEnabled:
                return await context.send('La recherche Spotify n\'a pas été configurée')
            if query.startswith("https://open.spotify.com/"):
                query = query[len("https://open.spotify.com/"):].replace('/', ':')
            else:
                query = query[len("spotify:"):]

            try:
                [_type, _id] = query.split(':')
                # Spotify link
                if _type == 'track':
                    track = Spotify.getTrack(_id)
                    query = "%s %s" % (track['name'], track['artists'][0]['name'])
                elif _type == 'playlist':
                    return await context.send('Fonction non prise en charge pour le moment')
            except:
                return await context.send('Le lien n\'est pas valide')

        if (query.startswith("http") or query.startswith("udp://")) and not query.startswith(("https://youtu.be", "https://www.youtube.com", "https://youtube.com")):
            # Other streams
            entry = Entry(query, context.author)
            position = await queue.addEntry(entry)
            await context.send("%d: %s a été ajouté à la file d\'attente" % (position, query))
        else:
            # Search YouTube
            if not query.startswith("https://"):
                message = await context.send("Recherche de \"%s\"..." % query)
                try:
                    result = await Youtube.searchVideos(query)
                except:
                    return await message.edit(content='Aucune musique trouvé')
                url = result["link"]
                # print(url)
            else:
                message = await context.send("Investigation sur \"%s\"..." % query[8:])
                url = query

            try:
                data = await Youtube.fetchData(url, self.bot.loop)
                print(data['webpage_url'])
            except:
                return await context.send('Le lien n\'est pas valide')

            applicant = context.author
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
                        await Youtube.downloadAudio(data['webpage_url'], message, text, self.bot.loop),
                    except:
                        return await message.edit(content="Erreur lors du téléchargement de %s" % data['title'])
                    fileSize = os.path.getsize(config.downloadDirectory + filename)

                if Queues[guild].voice_client.is_connected():
                    entry = Entry(filename, applicant, fileSize)
                    entry.buildMetadataYoutube(data)
                    position = await queue.addEntry(entry)
                    await message.edit(content="%d: %s a été ajouté à la file d\'attente" % (position, data['title']))
                else:
                    print("not connected")

    @commands.command(aliases=['np', 'en lecture'])
    async def nowplaying(self, context):
        guild = context.guild.id
        if guild not in Queues or Queues[guild].cursor == Queues[guild].size:
            return await context.send('Rien en lecture')
        else:
            await self.info(context, Queues[guild].cursor)

    @commands.command(aliases=['i'])
    async def info(self, context, index: int = None):
        guild = context.guild.id
        Queues[guild].voice_client = context.voice_client
        if guild not in Queues:
            return await context.send('Aucune liste d\'attente')

        if index is None:
            return await context.send(embed=Help.get(context, 'music', 'info'))

        if index < Queues[guild].size and index >= 0:
            entry = Queues[guild].content[index]

            content = "Chaîne : [%s](%s)\n" % (entry.channel, entry.channel_url)
            if Queues[guild].cursor == index:
                pause = "[Paused]" if Queues[guild].voice_client.is_paused() else ""
                current = Queues[guild].pausetime - Queues[guild].starttime if Queues[guild].voice_client.is_paused() else time.time() - Queues[guild].starttime
                
                if entry.duration == 0:
                    content += "Progression : %s %s\n" % (time_format(current), pause)
                else:
                    content += "Progression : %s/%s %s\n" % (time_format(current), time_format(entry.duration), pause)
                    progress = (current/entry.duration)*20
                    content += "["
                    for i in range(0,20):
                        if int(progress) == i:
                            content += "●"
                        else:
                            content += "─"
                    content += "] (%s%s)\n" % (int((current/entry.duration)*100),'%')


            if entry.album is not None:
                content += "Album : %s\n" % (entry.album)
            if entry.playlist is not None:
                content += "Playlist : [%s](%s)\n" % (entry.playlist.title, entry.playlist.url)
            content += "Position : %d" % index

            embed = discord.Embed(
                title=entry.title,
                url=entry.url,
                description=content,
                color=0x565493
            )

            if Queues[guild].cursor == index:
                bigPause = "❚❚" if Queues[guild].voice_client.is_paused() else "▶"
                name = bigPause + "\t" + (" En pause" if Queues[guild].voice_client.is_paused() else " En cours de lecture")
            else:
                name = "Informations piste"
            embed.set_author(name=name, icon_url = self.bot.user.display_avatar.url)
            embed.set_image(url=entry.thumbnail)
            #embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text="Demandé par %s" % entry.applicant.display_name, icon_url = entry.applicant.display_avatar.url)

            return await context.send(embed=embed)
        else:
            return await context.send('L\'index %d n\'existe pas' % (index))

    @commands.command(aliases=['q', 'file', 'dir', 'ls'])
    async def queue(self, context, page:int = None):
        guild = context.guild.id
        if guild not in Queues:
            return await context.send('Aucune liste d\'attente')

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
                return await context.send('Index de page invalide')
            
            printMin = (page - 1)*printSize
            printMax = min(printMin + printSize, Queues[guild].size)
        
        if printMin == 0:
            list += "==== Début de la file\n"
        else:
            list += "⠀⠀⠀⠀…\n"
            
        for i in range(printMin, printMax):
            entry = Queues[guild].content[i]
            if entry.playlist is not None:
                tab = "⠀⠀⠀⠀"
                if entry.playlist.id != current_playlist:
                    current_playlist = entry.playlist.id
                    if Queues[guild].repeat_mode == "playlist":
                        list += "⟳⠀"
                    else:
                        list += "⠀⠀"
                    list += " Playlist : %s\n" % entry.playlist.title
            else:
                tab = ""
                current_playlist = ""
            totalDuration += entry.duration
            totalSize += entry.fileSize
            indicator = "⠀⠀ "
            if Queues[guild].cursor == i:
                if Queues[guild].repeat_mode == "entry":
                    indicator = "⟳⠀"
                else:
                    indicator = "→⠀"

            list += "%s%s%d: %s - %s - %.2fMo\n" % (tab, indicator, i, entry.title, time_format(entry.duration), entry.fileSize/1000000)
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
        footerText = "Nombre d'entrées : %d | Mode de répétition : %s\nDurée totale : %s | Taille totale : %.2fMo" % (Queues[guild].size, repeat_text[Queues[guild].repeat_mode], time_format(totalDuration), totalSize/1000000)
        if page is not None:
            footerText += "\nPage %d/%d" % (page, ((Queues[guild].size - 1) // printSize) + 1)
        embed.set_author(name = "Liste de lecture", icon_url = self.bot.user.avatar.url)
        embed.set_footer(text = footerText)

        return await context.send(embed=embed)

    @commands.command(aliases=['mv', 'déplacer', 'bouge'])
    async def move(self, context, frm: int = None, to: int = None):
        guild = context.guild.id
        if guild not in Queues:
            return await context.send('Aucune liste d\'attente')

        if frm is None or to is None:
            return await context.send(embed=Help.get(context, 'music' 'move'))

        if frm == to:
            return await context.send('La destination ne peut pas être égale à la source')

        if frm < Queues[guild].size and frm >= 0 and to < Queues[guild].size and to >= 0:
            title = Queues[guild].getEntry(frm).title
            Queues[guild].moveEntry(frm, to)
            return await context.send('%s a été déplacé de %d vers %d' % (title, frm, to))
        else:
            return await context.send('Une des deux positions est invalide')

    @commands.command(aliases=['rm', 'supprimer', 'enlever'])
    async def remove(self, context, idx1: str = None, idx2: str = None):
        guild = context.guild.id
        Queues[guild].voice_client = context.voice_client
        if guild not in Queues:
            return await context.send('Aucune liste d\'attente')

        if idx1.isdigit():
            idx1 = int(idx1)
        else:
            return await context.send(embed=Help.get(context, 'music', 'remove'))
                    
        if idx1 >= Queues[guild].size or idx1 < 0:
            return await context.send('L\'index 1 (%d) n\'existe pas dans la queue' % (idx1))
        
        if idx2 is None: # remove one entry
            entry = Queues[guild].getEntry(idx1)
            if idx1 == Queues[guild].cursor:
                Queues[guild].voice_client.stop()
            Queues[guild].removeEntry(idx1)
            if idx1 <= Queues[guild].cursor:
                Queues[guild].cursor -= 1
            if entry.filename in os.listdir(config.downloadDirectory):
                os.remove(config.downloadDirectory + entry.filename)
            return await context.send('%s a bien été supprimé' % (entry.title))
        else: # remove multiple entries
            if idx2.isdigit():
                idx2 = int(idx2) + 1
            elif idx2 == "-":
                idx2 = Queues[guild].size
            else:
                return await context.send(embed=Help.get(context, 'music', 'remove'))

            oldSize = Queues[guild].size
            if idx2 > oldSize or idx2 < 0:
                return await context.send('L\'index 2 (%d) n\'existe pas dans la queue' % (idx1))
            if idx1 > (idx2 - 1):
                return await context.send("Attention à l'ordre des index !")
            if idx1 <= Queues[guild].cursor <= idx2 - 1:
                Queues[guild].voice_client.stop()
            for i in range(idx2 - idx1):
                entry = Queues[guild].getEntry(idx1)
                Queues[guild].removeEntry(idx1)
                if idx1 <= Queues[guild].cursor:
                    Queues[guild].cursor -= 1
                if entry.filename in os.listdir(config.downloadDirectory):
                    os.remove(config.downloadDirectory + entry.filename)
            return await context.send("Les entrées commençant à %d jusqu'à %s ont bien été supprimés" % (idx1, "la fin de la liste" if idx2 == oldSize else str(idx2 - 1)))

    @commands.command(aliases=['sk'])
    async def seek(self, context, timeCode: str = None):
        guild = context.guild.id
        Queues[guild].voice_client = context.voice_client

        if guild not in Queues:
            return await context.send('Pas de lecture en cours')

        if timeCode is None:
            return await context.send(embed=Help.get(context, 'music', 'info'))

        currentEntry = Queues[guild].content[Queues[guild].cursor]
        if currentEntry.duration <= 0:
            return await context.send("Ce morceau n'est pas seekable")

        #Decoding timeCode
        if timeCode is not None:
            try:
                time = list(map(int, timeCode.split(":")))[::-1]
            except:
                return await context.send("Quelque chose ne va pas dans la syntaxe (doit être hh:mm:ss ou mmmm:ss ou bien ssss)")
        else:
            return await context.send(embed=Help.get(context, 'music', 'play'))
        (secs, mins, hrs) = (0,0,0)
        secs = time[0]
        if len(time) > 1:
            if 0 <= secs < 60:
                mins = time[1]
            else:
                return await context.send("Le temps n'est pas conforme")
            if len(time) > 2:
                if  0 <= mins < 60:
                    hrs = time[2]
                else:
                    return await context.send("Le temps n'est pas conforme")
                if hrs < 0:
                    return await context.send("Le temps n'est pas conforme")
        desiredStart = secs + 60*mins + 60*60*hrs
        
        if 0 <= desiredStart < currentEntry.duration -1:
            Queues[guild].repeat_bypass = True
            Queues[guild].seekTime = desiredStart
            Queues[guild].voice_client.stop()
        else:
            return await context.send("La vidéo sera déjà finie à %s..." % (time_format(desiredStart)))
        


    @commands.command(aliases=['s', 'passer', 'next', 'suivant'])
    async def skip(self, context):
        guild = context.guild.id
        #voiceClient = context.voice_client

        if guild in Queues:
            if Queues[guild].cursor < Queues[guild].size:
                Queues[guild].repeat_bypass = True
                Queues[guild].cursor = Queues[guild].cursor + 1
                Queues[guild].voice_client.stop()
            else:
                return await context.send('Rien à passer')
        else:
            return await context.send('Aucune lecture en cours')

    @commands.command(aliases=['pauser', 'suspendre', 'sus', 'halte'])
    async def pause(self, context):
        guild = context.guild.id
        #voiceClient = context.voice_client
        
        if guild in Queues:
            if Queues[guild].voice_client.is_playing():
                Queues[guild].voice_client.pause()
                Queues[guild].pausetime = time.time()
                return await context.send('Mis en pause')
            else:
                return await context.send('Déjà en pause')
        else:
            return await context.send('Aucune lecture en cours sur ce serveur')

    @commands.command(aliases=['reprendre'])
    async def resume(self, context):
        guild = context.guild.id
        #voiceClient = context.voice_client
        
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

    @commands.command(aliases=['arreter', 'stopper', 'shutup', 'tg'])
    async def stop(self, context):
        guild = context.guild.id
        #voiceClient = context.voice_client
        
        if Queues[guild].voice_client is not None:
            if Queues[guild].voice_client.is_playing or Queues[guild].voice_client.is_paused:
                if context.author.voice is None or context.author.voice.channel != Queues[guild].voice_client.channel:
                    return await context.send("Je suis en train de jouer de la musique là, viens me le dire en face !")
                Queues[guild].repeat_bypass = True
                Queues[guild].voice_client.stop()
                return await context.send("Ok j'arrête de lire la musique :(")
        else:
            return await context.send("Je suis pas connecté sur ce serveur en fait !")

    @commands.command(aliases=['quitter', 'deconnexion', 'deco', 'ntm', 'l'])
    async def leave(self, context):
        guild = context.guild.id
        #voiceClient = context.voice_client

        if Queues[guild].voice_client is not None:
            if Queues[guild].voice_client.is_playing() and (context.author.voice is None or context.author.voice.channel != Queues[guild].voice_client.channel):
                return await context.send("Je suis en train de jouer de la musique là, viens me le dire en face !")
            Queues[guild].voice_client.stop()
            Queues[guild].voice_client.cleanup()
            await Queues[guild].voice_client.disconnect()
            if guild in Queues:
                for entry in Queues[guild].content:
                    if entry.filename in os.listdir(config.downloadDirectory): #TODO implement waiting for process to stop using the file before trying to remove it
                        try:
                            os.remove(config.downloadDirectory + entry.filename) # ATM (if running on Windows), the file currently playing will not be erased
                        except:
                            print("error remove")
            Queues.pop(guild)
            return await context.send('Ok bye!')
        else:
            return await context.send('Je suis pas connecté en fait !')

    @commands.command(aliases=['r', 'repeter'])
    async def repeat(self, context, mode: str = None):
        guild = context.guild.id

        if guild not in Queues:
            return await context.send('Aucune liste d\'attente')

        repeat_modes = ["none", "entry", "all", "playlist"]
        if mode is not None:
            if mode not in repeat_modes:
                return await context.send(embed=Help.get(context, 'music', 'repeat'))
            else:
                new_mode = mode
                Queues[guild].repeat_mode = new_mode
        else:
            old_mode = Queues[guild].repeat_mode
            new_mode = repeat_modes[(repeat_modes.index(old_mode) + 1) % len(repeat_modes)]
            Queues[guild].repeat_mode = new_mode

        return await context.send('Le mode de répétition à été changé sur %s' % new_mode)

    @commands.command(aliases=['g', 'go', 'gt'])
    async def goto(self, context, index: int = None):
        guild = context.guild.id
        #voiceClient = context.voice_client
        if guild not in Queues:
            return await context.send('Aucune liste d\'attente')

        if index is None:
            return await context.send(embed=Help.get(context, 'music', 'goto'))

        if index < Queues[guild].size and index >= 0:
            Queues[guild].cursor = index
            if Queues[guild].voice_client.is_playing() or Queues[guild].voice_client.is_paused():
                Queues[guild].repeat_bypass = True
                Queues[guild].voice_client.stop()
            else:
                await Queues[guild].startPlayback()
            return  # await context.send('Direction la musique n°%d' % index)
        else:
            return await context.send('L\'index %d n\'existe pas' % index)
    
    #afk loop
    @tasks.loop(seconds=activityCheckDelta)
    async def musicTimeout(self):
        GuildsToDisconnect = []
        for guild in Queues.keys():
            if Queues[guild].voice_client is not None:
                if Queues[guild].isPlaying():
                    Queues[guild].voiceActivityUpdate()
                else:
                    if time.time() - Queues[guild].lastVoiceActivityTime >= config.afkLeaveTime*60:
                        GuildsToDisconnect.append(guild)
            else:
                print("Guild (%d): no voice" % (guild))
        if len(GuildsToDisconnect) > 0:
            for id in GuildsToDisconnect:
                # membersInVoice = len(Queues[guild].getVoiceChannel().members)
                # if membersInVoice > 1:
                #     await Queues[id].text_channel.send("Je m'en vais (ça fait au moins %d minutes qu'il n'y a plus de musique)" % (config.afkLeaveTime))
                await Queues[id].disconnect()
                print(("Guild (%d): Disconnected for inactivity" % (guild)))
                for entry in Queues[id].content:
                    if entry.filename in os.listdir(config.downloadDirectory): #TODO implement waiting for process to stop using the file before trying to remove it
                        os.remove(config.downloadDirectory + entry.filename) #If running on Windows, the file currently playing is not erased
                Queues.pop(id)
        
        
def pickSoundFile(folderName):
    fPath = config.soundDirectory + folderName
    if os.path.isdir(fPath):
        if len(os.listdir(fPath)) > 0:
            rnd = random.randint(0, len(os.listdir(fPath))-1)
            return True, "%s/%s" % (fPath, os.listdir(fPath)[rnd])
        else:
            return True, "" # Folder exist but no file found
    else: 
        return False, "" # Folder does not exist

