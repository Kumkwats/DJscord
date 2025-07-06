#import os
#import asyncio

import discord
#from discord.channel import VoiceChannel
#from discord.ext import commands

from DJscordBot.djscordBot import DJscordBot
from DJscordBot.discord.utils import InteractionWrapper

#from DJscordBot.config import config
#from DJscordBot.utils import pick_sound_file
from DJscordBot.Managers.queueManager import QueueManager

class Manage():
    def __init__(self, bot: DJscordBot):
        self.bot = bot

    async def ping(self, ctx: InteractionWrapper): # Show latency from API and Voice channel if connected
        msg = "Pong!"
        msg += "\n`%1.0f ms` avec l'API" % (round(self.bot.latency*1000))
        voice_client: discord.VoiceClient = ctx.interaction.guild.voice_client
        if voice_client is not None:
            if(voice_client.average_latency != float('inf')):
                msg += "\n`%1.0f ms` sur %s" % (round(voice_client.average_latency*1000), voice_client.channel.name)
            else:
                msg += "\n`ping indisponible...` sur %s" % (voice_client.channel.name)
        await ctx.respond(msg)

    # @commands.command(description="est-ce que c'est pété ?")
    async def cpt(self, ctx: InteractionWrapper):
        await ctx.respond("Est-ce que c'est pété ? Voici ce qu'il faut savoir:" +
                                "\n# oui" + 
                                "\n\n||(@\\Kkum si problème)||")
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
    
    


    
