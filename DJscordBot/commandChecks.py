import discord
from discord.ext import commands

@commands.check
def is_connected_to_vc(ctx: discord.ApplicationContext):
    if ctx.author.voice is None:
        return False
    if ctx.author.voice.channel is not None:
        return True
    return False