import os
import discord

from config import config
from help import Help
from music import Music
from manage import Manage
from debug import Debug
from fun import Fun


if config.FoxDotEnabled is True:
    from foxdot import Foxdot

if __name__ == "__main__":
    if os.path.isdir(config.downloadDirectory): # Preparing download folder
        for f in os.listdir(config.downloadDirectory):
            os.remove(config.downloadDirectory + f)
    else:
        os.mkdir(config.downloadDirectory)

    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True

    bot = discord.Bot(description="hello", intents=intents)

    #TODO make error send a message to the author ??
    @bot.event
    async def on_ready():
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=config.getPrefix()+"help"))
        print('Logged in as {0} ({0.id})'.format(bot.user))
        print('----------------')

    @bot.event
    async def on_message(message: discord.Message):
        if(message.author.bot):
            return
        await Fun.chocolatine(message)

    
    musicCog = Music(bot)
    @bot.command(description="jouer musique")
    async def play(ctx: discord.ApplicationContext, recherche: str):
        await musicCog.play(ctx, recherche)

    @bot.command(description="jouer musique")
    async def goto(ctx: discord.ApplicationContext,
                   index: discord.Option(int, min_value=0)):
        await musicCog.goto(ctx, index)

    @bot.command(description="passer musique")
    async def skip(ctx: discord.ApplicationContext):
        await musicCog.skip(ctx)

    @bot.command(description="STOP")
    async def stop(ctx: discord.ApplicationContext):
        await musicCog.stop(ctx)

    queue: discord.SlashCommandGroup = bot.create_group("queue", "OwO la queue")

    @queue.command(name="page", description="affiche une page de la *queue*")
    async def qPage(ctx: discord.ApplicationContext,
                        page: discord.Option(int,
                                             description="id de la page",
                                             min_value=1)):
        await musicCog.queue(ctx, page)

    @queue.command(name="current", description="affiche la *queue* autour de la lecture en cours")
    async def qCurrent(ctx: discord.ApplicationContext):
        await musicCog.queue(ctx, None)

    @queue.command(description="déplace une musique")
    async def move(ctx: discord.ApplicationContext,
                   frm: discord.Option(int,
                                       name="from",
                                       min_value=0),
                   to: discord.Option(int, min_value=0)):
        await musicCog.move(ctx, frm, to)

    @queue.command(description="enlève une musique")
    async def remove(ctx: discord.ApplicationContext,
                     index: discord.Option(int,
                                           min_value=0)):
        await musicCog.remove(ctx, index)

    #TODO: range - last
    @queue.command(description="enlève des musiques")
    async def remove_range(ctx: discord.ApplicationContext,
                           start: discord.Option(int, min_value=0),
                           end: discord.Option(int, min_value=0)):
        await musicCog.remove(ctx, start, end)

    @queue.command(description="affiche les infos pour la lecture en cours")
    async def info(ctx: discord.ApplicationContext,
                   index: discord.Option(int,
                                         description="numéro de la chanson dans la *queue*",
                                         min_value=0)):
        await musicCog.info(ctx, index)


    @bot.command(description="affiche les infos pour la lecture en cours")
    async def nowplaying(ctx: discord.ApplicationContext):
        await musicCog.nowplaying(ctx)    


    #TODO description of timeCode
    @bot.command(description="va a une partie spécifique de la musique")
    async def seek(ctx: discord.ApplicationContext, time_code: str):
        await musicCog.seek(ctx, time_code)

    @bot.command(description="oust")
    async def leave(ctx: discord.ApplicationContext):
        await musicCog.leave(ctx)


    @bot.command(description="choisir le mode de répétition")
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
