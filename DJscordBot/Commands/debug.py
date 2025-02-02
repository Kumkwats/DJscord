import discord
from discord.ext import commands

# pylint: disable=C0115,C0116,C0303

class Debug(commands.Cog):
    @commands.command()
    @commands.is_owner()
    async def info_voice_client(self, context: discord.ApplicationContext):
        voice_client = context.voice_client
        
        message = "Info Voice Client :"
        if voice_client is None:
            message += "\n**Pas de voice client**"
            return await context.send(message)
        message += f"\n - is_connected = {voice_client.is_connected()}"
        message += f"\n - channel = `{voice_client.channel.name}`"
        message += f"\n - is_playing = **{voice_client.is_playing()}**"
        return await context.send(message)

    @info_voice_client.error
    async def info_voice_client_error(self, context, error): # Connect without playing music
        if isinstance(error, commands.NotOwner):
            return await context.send(f"Nan t'as pas le droit {context.author.display_name}")
        print(error)
        return await context.send("Something is wrong, I can feel it...")

    # @commands.command()
    # @commands.is_owner()
    # async def people_in_voice_chat(self, context):
    #     context.voice_client
    #     return await context.send((context.voice_client.channel.members))

    @commands.command()
    @commands.is_owner()
    async def connect(self, context: discord.ApplicationContext): # Connect without playing music
        author_voice = context.author.voice
        voice_client = context.voice_client

        if author_voice is not None:
            if voice_client is not None:
                await voice_client.move_to(author_voice.channel)
            else:
                await author_voice.channel.connect(timeout=600, reconnect=True)
            await context.send("Connecté !")
        else:
            await context.send("Connecte toi d'abord en fait...")


    @connect.error
    async def connect_error(self, context: discord.ApplicationContext, error):
        if isinstance(error, commands.NotOwner):
            return await context.send(f"Nan t'as pas le droit {context.author.display_name}")
        print(error)
        return await context.send("Something is wrong, I can feel it...")