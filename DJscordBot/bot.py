import traceback
from datetime import datetime, timezone
import asyncio

import discord
from discord import app_commands, Interaction


from .app import ROOT_LOGGER
from .client import DJscordClient
from .logging.utils import get_logger

from .config import config
from .utils.discord import InteractionWrapper

from .commands.music import Music
from .commands.manage import Manage
from .commands.fun import chocolatine

from .ServiceProviders.spotify import SPOTIFY_AVAILABLE

__logger = get_logger(f"{ROOT_LOGGER}")


BOT_CLIENT: DJscordClient


def create_intents() -> discord.Intents:
    intents: discord.Intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    return intents



def setup_events():
    __logger.debug("Registering events...")

    @BOT_CLIENT.event
    async def on_ready():
        """called when the bot is logged in and ready to process commandes
        """
        ready_activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="/play",
            state="\"/queue current\" is a bad command name")
        
        await BOT_CLIENT.change_presence(activity=ready_activity)
        
        __logger.info(f"[READY] Logged in as {BOT_CLIENT.user} ({BOT_CLIENT.user.id})\n---------------- BEGIN LISTENING TO COMMANDS")

    @BOT_CLIENT.event
    async def on_connect():
        __logger.info("[CONNECT] Established connection with Discord")
        pass
    
    @BOT_CLIENT.event
    async def on_disconnect():
        __logger.info("[CONNECT] Disconnected from Discord")
        pass

    @BOT_CLIENT.event
    async def on_error(event: str, *args, **kwargs):
        __logger.error(f"[BOT.ERROR] An error happened on the event {event}\n" + 
              f"\t args: {args}"+
              f"\t kwargs: {kwargs}")
        pass

    @BOT_CLIENT.event
    async def on_resumed():
        __logger.info("[SESSION] Session resumed")
        pass


    @BOT_CLIENT.event
    async def on_message(message: discord.Message):
        """Called when a message is posted on any channel the bot is allowed to read

        Args:
            message (discord.Message): the Discord message sent
        """

        if not message.author.bot:
            await chocolatine(message)



def setup_commands():
    global BOT_CLIENT

    __logger.debug("Registering commands...")
    musicCog = Music(BOT_CLIENT)

    # setup descriptions
    descriptions: 'dict[str,str]' = {}
    descriptions["play"] = "Recherche YT ou bien un lien vers une vidéo ou une playlist"
    if SPOTIFY_AVAILABLE:
        descriptions["play"] += " (prends aussi en charge les titres, albums et playlists Spotify)"

    @BOT_CLIENT.tree.command(description="Jouer musique")
    @app_commands.guild_only()
    @app_commands.rename(search_query="recherche")
    @app_commands.describe(search_query=descriptions["play"])
    async def play(ctx: Interaction, search_query: str):
        await musicCog.cmd_play(InteractionWrapper(ctx), search_query)

    

    @play.error
    async def play_error(ctx: Interaction, error: app_commands.AppCommandError):
        __logger.error(f"An error occured in the play command\ntraceback:\n{traceback.print_exception(error)}")
        error_message = ":warning: Une erreur est survenue pendant le traitement de la requète"
        if ctx.response.is_done:
            await ctx.followup.send(error_message, ephemeral=True)
        else:
            await ctx.response.send_message(error_message, ephemeral=True)



    @BOT_CLIENT.tree.command(description="Selection musique")
    @app_commands.guild_only()
    @app_commands.describe(index="Position où sera déplacé le curseur de la liste de lecture")
    async def goto(ctx: Interaction, index: app_commands.Range[int, 0, None]):
        await musicCog.goto(InteractionWrapper(ctx), index)


    @BOT_CLIENT.tree.command(description="Passer musique")
    @app_commands.guild_only()
    async def skip(ctx: Interaction):
        await musicCog.skip(InteractionWrapper(ctx))
    
    @BOT_CLIENT.tree.command(description="Pause musique")
    @app_commands.guild_only()
    async def pause(ctx: Interaction):
        await musicCog.pause(InteractionWrapper(ctx))

    @BOT_CLIENT.tree.command(description="Reprendre musique")
    @app_commands.guild_only()
    async def resume(ctx: Interaction):
        await musicCog.resume(InteractionWrapper(ctx))

    @BOT_CLIENT.tree.command(description="STOP")
    @app_commands.guild_only()
    async def stop(ctx: Interaction):
        await musicCog.stop(InteractionWrapper(ctx))


    #region Queue
    queue: app_commands.Group = app_commands.Group(name="queue", description="OwO la queue")



    @queue.command(name="page", description="Affiche une page de la *queue*")
    @app_commands.describe(page="Numéro de la page à afficher")
    async def queue_page(ctx: Interaction, page: app_commands.Range[int, 1, None]):
        await musicCog.print_queue(InteractionWrapper(ctx), page)


    @queue.command(name="current", description="Affiche la *queue* autour de la lecture en cours")
    async def queue_current(ctx: Interaction):
        await musicCog.print_queue(InteractionWrapper(ctx))



    @queue.command(name="move", description="Déplace une musique dans la *queue*")
    @app_commands.rename(frm="from", to="to")
    @app_commands.describe(frm="Position de la musique à déplacer", to="Nouvelle position de la musique")
    async def queue_move(ctx: Interaction, frm: app_commands.Range[int, 0, None], to: app_commands.Range[int, 0, None]):
        await musicCog.move(InteractionWrapper(ctx), frm, to)





    @queue.command(name="remove", description="Enlève une musique")
    @app_commands.describe(index="Position de la musique à enlever")
    async def queue_remove(ctx: Interaction, index: app_commands.Range[int, 0, None]):
        await musicCog.remove(InteractionWrapper(ctx), index)


    @queue.command(name="remove_range",description="Enlève **des** musiques")
    @app_commands.describe(start="Position de la première musique à enlever", end="Position de la dernière musique à enlever")
    async def queue_remove_range(ctx: Interaction, start: app_commands.Range[int, 0, None], end: app_commands.Range[int, 0, None]):
        await musicCog.remove(InteractionWrapper(ctx), start, end)


    @queue.command(name="info", description="Affiche les infos pour une musique de la *queue*")
    @app_commands.describe(index="Position de la musique dans la *queue*")
    async def queue_info(ctx: Interaction, index: app_commands.Range[int, 0, None]):
        await musicCog.info(InteractionWrapper(ctx), index)

    from DJscordBot.Types.enums import RepeatMode
    @queue.command(description="Choisir le mode de répétition")
    async def repeat(ctx: Interaction, mode: RepeatMode = RepeatMode.NONE):
        await musicCog.repeat(InteractionWrapper(ctx), mode)

    BOT_CLIENT.tree.add_command(queue)

    #endregion



    


    @BOT_CLIENT.tree.command(description="Affiche les infos pour la lecture en cours")
    async def nowplaying(ctx: Interaction):
        await musicCog.now_playing(InteractionWrapper(ctx))


    #TODO description of timeCode
    @BOT_CLIENT.tree.command(description="Va a une partie spécifique de la musique")
    @app_commands.describe(time_code="Position où placer le curseur de lecture dans la musique en cours")
    async def seek(ctx: Interaction, time_code: str):
        await musicCog.seek(InteractionWrapper(ctx), time_code)

    @BOT_CLIENT.tree.command(description="Allez oust !")
    async def leave(ctx: Interaction):
        await musicCog.leave(InteractionWrapper(ctx))





    #funCog = Fun(BOT_CLIENT)

    manageCog = Manage(BOT_CLIENT)
    @BOT_CLIENT.tree.command(description="pong ?")
    async def ping(ctx: Interaction):
        await manageCog.ping(InteractionWrapper(ctx))

    @BOT_CLIENT.tree.command(description="Est-ce que c'est pété ?")
    @app_commands.guild_install()
    async def cpt(ctx: Interaction):
        await manageCog.cpt(InteractionWrapper(ctx))
    #endregion

    # print("[BOT.COG] Added Debug Cog")
    # bot.add_cog(Debug(BOT_CLIENT))
    # print("[BOT.RUN] Running the bot")


async def __async_start(token:str):
    global BOT_CLIENT
    await BOT_CLIENT.login(token)
    await BOT_CLIENT.connect(reconnect=True)


def start_bot():
    global BOT_CLIENT
    BOT_CLIENT = DJscordClient(description="djscord !", intents=create_intents())

    setup_events()
    setup_commands()

    discord.utils.setup_logging(level=config.log_level)
    
    asyncio.run(__async_start(config.token))
