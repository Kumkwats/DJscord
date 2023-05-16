import os
import discord
import asyncio
from discord.channel import VoiceChannel
from discord.ext import commands, bridge
from config import config
from music import Queues, pickSoundFile

class Manage():
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    async def ping(self, ctx: discord.ApplicationContext): # Show latency from API and Voice channel if connected
        msg = "Pong!"
        msg += "\n`%1.0f ms` avec l'API" % (round(self.bot.latency*1000))
        voiceClient = ctx.voice_client
        if voiceClient is not None:
            if(voiceClient.average_latency != float('inf')):
                msg += "\n`%1.0f ms` sur %s" % (round(voiceClient.average_latency*1000), voiceClient.channel.name)
            else:
                msg += "\n`ping indisponible...` sur %s" % (voiceClient.channel.name)
        await ctx.respond(msg)

    # @commands.command(description="est-ce que c'est pété ?")
    async def cpt(self, ctx: discord.ApplicationContext):
        await ctx.respond("Est-ce que c'est pété ? Voici ce qu'il faut savoir:" +
                          "\n\n**Implémentations manquantes:** `/pause`, `/resume` et `/shutdown`" +
                          "\n**Incertitudes:**" +
                          "\n\t\t-Déconnexion automatique du bot (normalement actif mais non vérifié)" +
                          "\n\t\t-Recherche Spotify pas testé" +
                          "\n**Bugs connus:**\n\t\t-`/queue random_range` supprime jusqu'à `end - 1` au lieu de `end`" +
                          "\n\nMais autrement TVB !\n||(@\Kkum si problème)||")
        #await ctx.resopnd("Nan ça va tkt")

    # @commands.command() # TODO None type error quand pas dans le channel ?
    # @commands.is_owner()
    # async def shutdown(self, ctx: discord.ApplicationContext):
    #     authorVoice = ctx.author.voice
    #     voiceClient = ctx.voice_client
        
    #     if authorVoice is not None:
    #         if voiceClient is not None:
    #             await voiceClient.move_to(authorVoice.channel)
    #         else:
    #             voiceClient = await authorVoice.channel.connect(timeout=600, reconnect=True)
    #     if voiceClient is not None:
    #         if voiceClient.is_playing():
    #             Queues.clear()
    #             voiceClient.stop()
    #         await ctx.send("Shuting down DJPatrice XP…")

    #         check, file = pickSoundFile("Shutdown")
    #         if check:
    #             if file != "":
    #                 player = discord.FFmpegPCMAudio(file, options="-vn")
    #                 voiceClient.play(player)
    #             else:
    #                 print("Aucun fichier pour le shutdown")
    #         else:
    #             print("dossier sounds inexistant")
            
    #         while voiceClient.is_playing():
    #             await asyncio.sleep(0.5)
    #         await ctx.send("Bye bye")
    #         await voiceClient.disconnect()
    #     await ctx.send("*User has left the channel*")
    #     for f in os.listdir(config.downloadDirectory):
    #         os.remove(config.downloadDirectory + f)
    #     exit(0)

    # @shutdown.error
    # async def shutdown_error(self, ctx: discord.ApplicationContext, error):
    #     if isinstance(error, commands.NotOwner):
    #         return await ctx.send("Wait a minute… who are you?")
    #     else:
    #         print(error)
    
    


    
