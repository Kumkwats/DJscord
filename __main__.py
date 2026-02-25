"""
Entry point of the bot
"""
import asyncio

from DJscordBot.init import init_environment
from DJscordBot.bot import start_bot


if __name__ == "__main__":
    init_environment()
    with asyncio.Runner() as runner:
        runner.run(start_bot())
