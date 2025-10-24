import discord
from discord import app_commands

from .logging.utils import get_logger
logger = get_logger("djscordbot.client")

class DJscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, description=""):
        super().__init__(intents=intents, description=description)
        self.tree = app_commands.CommandTree(self)
        logger.info("Client initialized")