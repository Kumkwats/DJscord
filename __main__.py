
"""Entry point of the bot
"""
import os
import traceback


import discord
from discord import app_commands, Intents, Interaction
from DJscordBot.djscordBot import DJscordBot

from DJscordBot.config import config

from DJscordBot.discord.utils import InteractionWrapper

from DJscordBot.commands.music import Music
from DJscordBot.commands.manage import Manage
from DJscordBot.commands.fun import Fun, chocolatine
# from DJscordBot.commands.debug import Debug



if __name__ == "__main__":

    if os.path.isdir(config.downloadDirectory): # Preparing download folder
        print("[BOT] Cleaning up download folder...")
        for f in os.listdir(config.downloadDirectory):
            os.remove(config.downloadDirectory + f)
    else:
        os.makedirs(config.downloadDirectory)
        print(f"[BOT] Created download folder in : {config.downloadDirectory}")


    intents = Intents.default()
    intents.messages = True
    intents.message_content = True


    bot: DJscordBot = DJscordBot(description="djscord !", intents=intents)
    
    print("[BOT] Starting up...")

    #TODO make error send a message to the author ??
    @bot.event
    async def on_ready():
        """called when the bot is logged in and ready to process commandes
        """
        await bot.change_presence(
            activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=config.GetPrefix()+"help"))

        print(f"[BOT.READY] Logged in as {bot.user} ({bot.user.id})")
        print('----------------')

    @bot.event
    async def on_connect():
        print("[BOT.CONNECTION] Established connection with Discord")
        pass
    
    @bot.event
    async def on_disconnect():
        print("[BOT.CONNECTION] Disconnected from Discord")
        pass

    # @bot.event
    # async def on_error(event: str, *args, **kwargs):
    #     print(f"[BOT.ERROR] An error happened on the event {event}\n" + 
    #           f"\t args: {args}"+
    #           f"\t kwargs: {kwargs}")
    #     pass

    @bot.event
    async def on_resumed():
        print("[BOT.SESSION] Session resumed")
        pass


    @bot.event
    async def on_message(message: discord.Message):
        """Called when a message is posted on any channel the bot is allowed to read

        Args:
            message (discord.Message): the Discord message sent
        """

        if not message.author.bot:
            await chocolatine(message)
        
        

    
    #region commands
    musicCog = Music(bot)

    play_description = "Recherche YT ou bien un lien vers une vidéo ou une playlist"
    if config.spotifyEnabled:
        play_description += " (prends aussi en charge les titres, album et playlist Spotify)"

    @bot.tree.command(description="Jouer musique")
    @app_commands.guild_only()
    @app_commands.describe(recherche=play_description)
    async def play(ctx: Interaction,
                   recherche: app_commands.Parameter(
                       display_name="Recherche ou lien",
                       description=play_description,
                       type=discord.AppCommandOptionType.integer,
                       required=True,
                       )):
        await musicCog.cmd_play(InteractionWrapper(ctx), recherche)

    @play.error
    async def play_error(ctx: Interaction, error: app_commands.AppCommandError):
        print(traceback.print_exception(error))
        return await ctx.response.send_message(":warning: Une erreur est survenue pendant le traitement de la requète", ephemeral=True)



    @bot.tree.command(description="Selection musique")
    @app_commands.guild_only()
    async def goto(ctx: Interaction,
                   index: app_commands.Parameter(
                       description="Position dans la liste à atteindre",
                       type=discord.AppCommandOptionType.integer,
                       min_value=0,
                       required=True,
                       )):
        await musicCog.goto(InteractionWrapper(ctx), index)

    @bot.tree.command(description="Passer musique")
    @app_commands.guild_only()
    async def skip(ctx: Interaction):
        await musicCog.skip(InteractionWrapper(ctx))
    
    @bot.tree.command(description="Pause musique")
    @app_commands.guild_only()
    async def pause(ctx: Interaction):
        await musicCog.pause(InteractionWrapper(ctx))

    @bot.tree.command(description="Reprendre musique")
    @app_commands.guild_only()
    async def resume(ctx: Interaction):
        await musicCog.resume(InteractionWrapper(ctx))

    @bot.tree.command(description="STOP")
    @app_commands.guild_only()
    async def stop(ctx: Interaction):
        await musicCog.stop(InteractionWrapper(ctx))


    #region Queue
    queue: app_commands.Group = app_commands.Group(name="queue", description="OwO la queue")



    @queue.command(name="page", description="Affiche une page de la *queue*")
    async def queue_page(ctx: app_commands.AppCommandContext,
                        page: app_commands.Parameter(
                            description="Numéro de la page",
                            type=discord.AppCommandOptionType.integer,
                            min_value=1,
                            required=True,
                            )):
        await musicCog.print_queue(InteractionWrapper(ctx), page)



    @queue.command(name="current", description="Affiche la *queue* autour de la lecture en cours")
    async def queue_current(ctx: app_commands.AppCommandContext):
        await musicCog.print_queue(InteractionWrapper(ctx))



    @queue.command(name="move", description="Déplace une musique")
    async def queue_move(ctx: app_commands.AppCommandContext,
                   frm: app_commands.Parameter(type=discord.AppCommandOptionType.integer,
                                               name="from",
                                               min_value=0),
                   to: app_commands.Parameter(type=discord.AppCommandOptionType.integer,
                                              min_value=0)):
        await musicCog.move(InteractionWrapper(ctx), frm, to)



    @queue.command(name="remove", description="Enlève une musique")
    async def queue_remove(ctx: app_commands.AppCommandContext,
                     index: app_commands.Parameter(type=discord.AppCommandOptionType.integer,
                                                   min_value=0)):
        await musicCog.remove(InteractionWrapper(ctx), index)



    @queue.command(name="remove_range",description="Enlève **des** musiques")
    async def queue_remove_range(ctx: app_commands.AppCommandContext,
                                 start: app_commands.Parameter(type=discord.AppCommandOptionType.integer,
                                                               min_value=0),
                                 end: app_commands.Parameter(type=discord.AppCommandOptionType.integer,
                                                             min_value=0)):
        await musicCog.remove(InteractionWrapper(ctx), start, end)



    @queue.command(name="info", description="Affiche les infos pour une musique de la *queue*")
    async def queue_info(ctx: app_commands.AppCommandContext,
                   index: app_commands.Parameter(type=discord.AppCommandOptionType.integer,
                                                 description="numéro de la chanson dans la *queue*",
                                                 min_value=0)):
        await musicCog.info(InteractionWrapper(ctx), index)


    bot.tree.add_command(queue)

    #endregion





    @bot.command(description="Affiche les infos pour la lecture en cours")
    async def nowplaying(ctx: app_commands.AppCommandContext):
        await musicCog.now_playing(InteractionWrapper(ctx))


    #TODO description of timeCode
    @bot.command(description="Va a une partie spécifique de la musique")
    async def seek(ctx: app_commands.AppCommandContext, time_code: str):
        await musicCog.seek(InteractionWrapper(ctx), time_code)

    @bot.command(description="oust")
    async def leave(ctx: app_commands.AppCommandContext):
        await musicCog.leave(InteractionWrapper(ctx))


    @bot.command(description="Choisir le mode de répétition")
    async def repeat(ctx: app_commands.AppCommandContext,
                     mode: app_commands.Parameter(type=discord.AppCommandOptionType.string,
                                                 choices=["none", "entry", "playlist", "all"])):
        await musicCog.repeat(InteractionWrapper(ctx), mode)


    funCog = Fun(bot)

    manageCog = Manage(bot)
    @bot.command(description="pong ?")
    async def ping(ctx: app_commands.AppCommandContext):
        await manageCog.ping(InteractionWrapper(ctx))

    @bot.command(description="Est-ce que c'est pété ?")
    async def cpt(ctx: app_commands.AppCommandContext):
        await manageCog.cpt(InteractionWrapper(ctx))
    #endregion

    # print("[BOT.COG] Added Debug Cog")
    # bot.add_cog(Debug(bot))
    # print("[BOT.RUN] Running the bot")
    bot.run(config.token)
