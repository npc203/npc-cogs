import pprint
from typing import Literal

import discord
from discord.utils import escape_markdown as escape

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify

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
                        pprint.pformat(msg.embeds[0].to_dict(), indent=4).replace("`", "​`"),
                        page_length=1994,
                    ):
                        await ctx.send(box(page))
                    if printit:
                        await ctx.send(
                            content="​\n\nRecreating embed..\n\n..",
                            embed=discord.Embed().from_dict(msg.embeds[0].to_dict()),
                        )
                else:
                    await ctx.send("Replied message has no embeds")
            else:
                await ctx.send("Message isn't reachable")
        else:
            await ctx.send("No reply found")

    @commands.command()
    @commands.is_owner()
    async def e(self, ctx):
        if hasattr(ctx.message, "reference") and ctx.message.reference != None:
            msg = ctx.message.reference.resolved
            if isinstance(msg, discord.Message):
                check = msg.content
                if "eval" in check.split("\n", 1)[0]:
                    check = check.split("\n", 1)[1]
                await ctx.invoke(ctx.bot.get_command("eval"), body=check)
            else:
                await ctx.send("Message isn't reachable")
        else:
            await ctx.send("No reply found")

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
