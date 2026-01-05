
"""Entry point of the bot
"""

from DJscordBot.init import init_environment
from DJscordBot.bot import start_bot


if __name__ == "__main__":

    init_environment()
    start_bot()
