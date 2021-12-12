import os
import discord
import asyncio
from discord.channel import VoiceChannel
from discord.ext import commands
from config import config, DLDIR


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

    @commands.command(aliases=['hutdown'])
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
                voiceClient.stop()
            player = discord.FFmpegPCMAudio(os.path.dirname(os.path.realpath(__file__)) + "/shutdown.webm", options="-vn")
            await context.send("Shuting down DJPatrice XP…")
            voiceClient.play(player)
            while voiceClient.is_playing():
                pass
            await voiceClient.disconnect()
        await context.send("Bye bye")
        for f in os.listdir(DLDIR):
            os.remove(DLDIR + f)
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



    # Debug commands

    @commands.command()
    @commands.is_owner()
    async def connect(self, context): # Connect without playing music
        authorVoice = context.author.voice
        voiceClient = context.voice_client

        if authorVoice is not None:
            if voiceClient is not None:
                await voiceClient.move_to(authorVoice.channel)
            else:
                await authorVoice.channel.connect(timeout=600, reconnect=True)
            await context.send("Connecté !")
        else:
            await context.send("Connecte toi d'abord en fait...")


    @connect.error
    async def connect_error(self, context, error, message): # Connect without playing music
        if isinstance(error, commands.NotOwner):
            return await context.send("Nan t'as pas le droit %s" % (message.author.display_name))
        else:
            print(error)
            return await context.send("Something is wrong, I can feel it...")

    @commands.command()
    async def ping(self, context):
        msg = "Pong!"
        msg += "\n`%1.0f ms` avec l'API" % (round(self.bot.latency*1000))

        voiceClient = context.voice_client
        if voiceClient is not None:
            if(voiceClient.average_latency != float('inf')):
                msg += "\n`%1.0f ms` sur %s" % (round(voiceClient.average_latency*1000), voiceClient.channel.name)
            else:
                msg += "\n`ping indisponible...` sur %s" % (voiceClient.channel.name)
        await context.send(msg)
