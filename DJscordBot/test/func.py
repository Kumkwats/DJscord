from discord import Interaction

async def TEST_FUNC(ctx: Interaction):
    print("[TEST.BEGIN] Begin TEST function")
    await ctx.response.send_message("Hello, world")
    print("[TEST.FINAL] Completion of the TEST function")
