import discord
from discord.ext import commands

class Debug(commands.Cog):
    @commands.command()
    @commands.is_owner()
    async def infoVC(self, context):
        voiceClient = context.voice_client
        message = "Info Voice Client :"
        if voiceClient is None:
            message += "\n**Pas de voice client**"
            return await context.send(message)
        message += "\n - is_connected = **%s**" % voiceClient.is_connected()
        message += "\n - channel = `%s`" % voiceClient.channel.name
        message += "\n - is_playing = **%s**" % voiceClient.is_playing()
        return await context.send(message)

    @infoVC.error
    async def infoVC_error(self, context, error): # Connect without playing music
        if isinstance(error, commands.NotOwner):
            return await context.send("Nan t'as pas le droit %s" % (context.author.display_name))
        else:
            print(error)
            return await context.send("Something is wrong, I can feel it...")

    @commands.command()
    @commands.is_owner()
    async def pplVC(self, context):
        context.voice_client
        return await context.send((context.voice_client.channel.members))

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
    async def connect_error(self, context, error):
        if isinstance(error, commands.NotOwner):
            return await context.send("Nan t'as pas le droit %s" % (context.author.display_name))
        else:
            print(error)
            return await context.send("Something is wrong, I can feel it...")