import discord
from discord import app_commands


class DJscordBot(discord.Client):
    def __init__(self, *, intents: discord.Intents, description=""):
        super().__init__(intents=intents, description=description)
        self.tree = app_commands.CommandTree(self)