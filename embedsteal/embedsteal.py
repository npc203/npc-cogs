from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
import pprint
from redbot.core.utils.chat_formatting import pagify, box

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class EmbedSteal(commands.Cog):
    """
    An embed reverser cog
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

    @commands.command(aliases=["ge", "stealembed"])
    async def getembed(self, ctx, printit: bool = False):
        if hasattr(ctx.message, "reference") and ctx.message.reference != None:
            msg = ctx.message.reference.resolved
            if isinstance(msg, discord.Message):
                if hasattr(msg, "embeds"):
                    for page in pagify(
                        pprint.pformat(msg.embeds[0].to_dict(), indent=4),
                        page_length=1990,
                    ):
                        await ctx.send(box(page, lang="json"))
                    if printit:
                        await ctx.send(
                            embed=discord.Embed().from_dict(msg.embeds[0].to_dict())
                        )
                else:
                    await ctx.send("Replied message has no embeds")
            else:
                await ctx.send("Message isn't reachable")
        else:
            await ctx.send("No reply found")

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
