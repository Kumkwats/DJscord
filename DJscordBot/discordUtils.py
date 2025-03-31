from discord import WebhookMessage, ApplicationContext

class DiscordWebhookMsgWraper:
    def __init__(self, context: ApplicationContext, currentMessage: WebhookMessage = None):
        self.context: ApplicationContext = context
        self.message: WebhookMessage = currentMessage

    async def WriteUserResponse(self, string: str, writeNewMessage: bool = False):
        if self.message is None or writeNewMessage:
            self.message = await self.context.respond(string, ephemeral = True)
        else:
            await self.message.edit(string)

    async def WriteGlobalResponse(self, string: str):
        await self.context.send(string)
