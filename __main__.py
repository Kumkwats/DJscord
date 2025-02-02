
"""Entry point of the bot
"""

import os
import discord

from DJscordBot.config import config

from DJscordBot.Commands.music import Music
from DJscordBot.Commands.manage import Manage
from DJscordBot.Commands.fun import Fun, chocolatine

if __name__ == "__main__":
    if os.path.isdir(config.downloadDirectory): # Preparing download folder
        for f in os.listdir(config.downloadDirectory):
            os.remove(config.downloadDirectory + f)
    else:
        os.makedirs(config.downloadDirectory)

    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True

    bot = discord.Bot(description="hello", intents=intents)

    #TODO make error send a message to the author ??
    @bot.event
    async def on_ready():
        """called when the bot is logged in and ready to process commandes
        """
        await bot.change_presence(
            activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=config.getPrefix()+"help"))

        print(f"Logged in as {bot.user} ({bot.user.id})")
        print('----------------')

    @bot.event
    async def on_message(message: discord.Message):
        """Called when a message is posted on any channel the bot is allowed to read

        Args:
            message (discord.Message): the Discord message sent
        """

        if message.author.bot:
            return
        
        await chocolatine(message)

    
    musicCog = Music(bot)
    @bot.command(description="Jouer musique")
    async def play(ctx: discord.ApplicationContext, recherche: str):
        await musicCog.play(ctx, recherche)

    @bot.command(description="Selection musique")
    async def goto(ctx: discord.ApplicationContext,
                   index: discord.Option(int, min_value=0)):
        await musicCog.goto(ctx, index)

    @bot.command(description="Passer musique")
    async def skip(ctx: discord.ApplicationContext):
        await musicCog.skip(ctx)

    @bot.command(description="STOP")
    async def stop(ctx: discord.ApplicationContext):
        await musicCog.stop(ctx)

    queue: discord.SlashCommandGroup = bot.create_group("queue", "OwO la queue")

    @queue.command(name="page", description="Affiche une page de la *queue*")
    async def queue_page(ctx: discord.ApplicationContext,
                        page: discord.Option(int,
                                             description="id de la page",
                                             min_value=1)):
        await musicCog.queue(ctx, page)

    @queue.command(name="current", description="Affiche la *queue* autour de la lecture en cours")
    async def queue_current(ctx: discord.ApplicationContext):
        await musicCog.queue(ctx)

    @queue.command(name="move", description="Déplace une musique")
    async def queue_move(ctx: discord.ApplicationContext,
                   frm: discord.Option(int,
                                       name="from",
                                       min_value=0),
                   to: discord.Option(int, min_value=0)):
        await musicCog.move(ctx, frm, to)

    @queue.command(name="remove", description="Enlève une musique")
    async def queue_remove(ctx: discord.ApplicationContext,
                     index: discord.Option(int,
                                           min_value=0)):
        await musicCog.remove(ctx, index)

    #TODO: range - last
    @queue.command(name="remove_range",description="Enlève **des** musiques")
    async def queue_remove_range(ctx: discord.ApplicationContext,
                           start: discord.Option(int, min_value=0),
                           end: discord.Option(int, min_value=0)):
        await musicCog.remove(ctx, start, end)

    @queue.command(name="info", description="Affiche les infos pour une musique de la *queue*")
    async def queue_info(ctx: discord.ApplicationContext,
                   index: discord.Option(int,
                                         description="numéro de la chanson dans la *queue*",
                                         min_value=0)):
        await musicCog.info(ctx, index)


    @bot.command(description="Affiche les infos pour la lecture en cours")
    async def nowplaying(ctx: discord.ApplicationContext):
        await musicCog.now_playing(ctx)


    #TODO description of timeCode
    @bot.command(description="Va a une partie spécifique de la musique")
    async def seek(ctx: discord.ApplicationContext, time_code: str):
        await musicCog.seek(ctx, time_code)

    @bot.command(description="oust")
    async def leave(ctx: discord.ApplicationContext):
        await musicCog.leave(ctx)


    @bot.command(description="Choisir le mode de répétition")
    async def repeat(ctx: discord.ApplicationContext,
                    mode: discord.Option(str, choices=["none", "entry", "playlist", "all"])):
        await musicCog.repeat(ctx, mode)


    funCog = Fun(bot)

    manageCog = Manage(bot)
    @bot.command(description="pong ?")
    async def ping(ctx: discord.ApplicationContext):
        await manageCog.ping(ctx)

    @bot.command(description="Est-ce que c'est pété ?")
    async def cpt(ctx: discord.ApplicationContext):
        await manageCog.cpt(ctx)

    bot.run(config.token)
