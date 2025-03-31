from discord.ext import commands
import socket
import asyncio

from DJscordBot.config import config

BUFFER = 2048


class Foxdot(commands.Cog):
    def __init__(self, bot):
        global instance
        instance = self
        self.bot = bot
        self.foxdot_started = False
        self.clientid = 0x00

    @commands.command()
    async def foxdot(self, context, query: str = None):
        if query == "start" and not self.foxdot_started:
            self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.clientsocket.connect((config.conf["FoxDot-address"], config.conf["FoxDot-port"]))
            self.clientsocket.send(b'\x01')

            response = bytearray(self.clientsocket.recv(BUFFER))
            if response[0] == 0x01:
                self.clientid = response[1]

            print(self.clientid)
            self.foxdot_started = True

        elif query == "stop" and self.foxdot_started:
            self.clientsocket.send(b'\x02')

            response = bytearray(self.clientsocket.recv(BUFFER))
            if response[0] == 0x02:
                self.clientsocket.close()
                self.foxdot_started = False

        else:
            await context.send("erreur")

    async def send_command(message):
        global instance
        self = instance
        if self.foxdot_started is True and not message.content.startswith(config.GetPrefix() + "foxdot"):
            lenght = len(message.content)
            self.clientsocket.send(b'\x03' + lenght.to_bytes(2, 'big') + message.content.encode())
