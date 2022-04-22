import os
import discord
import asyncio
from discord.channel import VoiceChannel
from discord.ext import commands
from config import config
from music import Queues, pickSoundFile

class Manage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='set-prefix')
    @commands.has_permissions(manage_messages=True)
    async def set_prefix(self, context, query: str = None):
        if " " in query:
            return await context.send("Préfixe invalide")

        prefix = query
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=prefix+"help"))
        config.setPrefix(prefix)
        return await context.send("Le préfixe a été défini sur %s" % (prefix))

    @set_prefix.error
    async def set_prefix_error(self, context, error):
        if isinstance(error, commands.MissingPermissions):
            return await context.send("Eh t'as pas les droits pour faire ça !")

    @commands.command(aliases=['hutdown']) # TODO None type error quand pas dans le channel ?
    @commands.is_owner()
    async def shutdown(self, context):
        authorVoice = context.author.voice
        voiceClient = context.voice_client
        
        if authorVoice is not None:
            if voiceClient is not None:
                await voiceClient.move_to(authorVoice.channel)
            else:
                voiceClient = await authorVoice.channel.connect(timeout=600, reconnect=True)
        if voiceClient is not None:
            if voiceClient.is_playing():
                Queues.clear()
                voiceClient.stop()
            await context.send("Shuting down DJPatrice XP…")

            check, file = pickSoundFile("Shutdown")
            if check:
                if file != "":
                    player = discord.FFmpegPCMAudio(file, options="-vn")
                    voiceClient.play(player)
                else:
                    print("Aucun fichier pour le shutdown")
            else:
                print("dossier sounds inexistant")
            
            while voiceClient.is_playing():
                pass
            await context.send("Bye bye")
            await voiceClient.disconnect()
        await context.send("*User has left the channel*")
        for f in os.listdir(config.downloadDirectory):
            os.remove(config.downloadDirectory + f)
        exit(0)

    @shutdown.error
    async def shutdown_error(self, context, error):
        if isinstance(error, commands.NotOwner):
            return await context.send("Wait a minute… who are you?")
        else:
            print(error)
    
    @commands.command(aliases=['ckc'])
    async def cpt(self, message):
        await message.reply("Nan ça va tkt")


    @commands.command()
    async def ping(self, context): # Show latency from API and Voice channel if connected
        msg = "Pong!"
        msg += "\n`%1.0f ms` avec l'API" % (round(self.bot.latency*1000))

        voiceClient = context.voice_client
        if voiceClient is not None:
            if(voiceClient.average_latency != float('inf')):
                msg += "\n`%1.0f ms` sur %s" % (round(voiceClient.average_latency*1000), voiceClient.channel.name)
            else:
                msg += "\n`ping indisponible...` sur %s" % (voiceClient.channel.name)
        await context.send(msg)
