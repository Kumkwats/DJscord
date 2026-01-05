import discord
from discord import app_commands

from .logging.utils import get_logger
__logger = get_logger("djscordbot.client")

class DJscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, description=""):
        global __logger
        super().__init__(intents=intents, description=description)
        self.tree = app_commands.CommandTree(self)
        __logger.info("Client initialized")
