"""Some silly little functions

Returns:
    _type_: _description_
"""

import re
import discord
from discord.ext import commands

# pylint: disable=C0115,C0116,C0303

class Fun(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.command()
    async def ah(self, context, *, query: str = None):
        if query == "quel plaisir":
            return await context.send('$ahh')

async def chocolatine(message: discord.Message):
    words = re.split('\\s+|\'|"', message.content)
    for word in words:
        if word.endswith("tine"):
            await message.reply(
                f"Sans te contredire {message.author.display_name}, " +
                f"on ne dit pas {word} mais pain au {word[:-3]} !")
