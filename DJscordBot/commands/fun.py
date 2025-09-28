"""Some silly little functions

Returns:
    _type_: _description_
"""

import re
import discord
from discord.ext import commands

from DJscordBot.djscordBot import DJscordBot

# class Fun(commands.Cog):
#     def __init__(self, bot: DJscordBot):
#         self.bot = bot

#     @commands.command()
#     async def ah(self, context, *, query: str = None):
#         if query == "quel plaisir":
#             return await context.send('$ahh')

async def chocolatine(message: discord.Message):
    words = re.split('\\s+|\'|"|,|!|\?', message.content)
    tine_words: list[str] = []

    for word in words:
        if word.endswith("tine"):
            tine_words.append(word)

    if len(tine_words) < 1:
        return
    
    #cleanup duplicates
    tine_words = list(dict.fromkeys(tine_words))

    if len(tine_words) == 1: #classic
        return await message.reply(f"Sans te contredire {message.author.display_name}, on ne dit pas {tine_words[0]} mais pain au {tine_words[0][:-3]} !")


    part1: str = ""
    part2: str = ""

    part1 += tine_words[0]
    part2 += f"pain au {tine_words[0][:-3]}"

    last_idx = len(tine_words)-1

    for idx in range(1, last_idx):
        part1 += f", {tine_words[idx]}"
        part2 += f", pain au {tine_words[idx][:-3]}"

    part1 += f" ou {tine_words[last_idx]}"
    part2 += f" et pain au {tine_words[last_idx][:-3]}"

    return await message.reply(f"Sans te contredire {message.author.display_name}, on ne dit pas {part1} mais {part2} !")


    
