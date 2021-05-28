from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
import asyncio

from .utils import BoardMenu


class TicTac(commands.Cog):
    """
    A small tic tac game with multiplayer and AI
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

    @commands.command()
    async def ttt(self, ctx, member: discord.Member):
        tick = "\N{WHITE HEAVY CHECK MARK}"
        init = await ctx.send(
            f"`{ctx.author.display_name}` challenges for a match of tic tac toe with `{member.display_name}`, react with a {tick} to play."
        )
        await init.add_reaction(tick)
        try:
            await self.bot.wait_for(
                "reaction_add",
                timeout=30,
                check=lambda r, u: u.id == member.id
                and str(r.emoji) == tick
                and r.message.id == init.id,
            )
        except asyncio.TimeoutError:
            return await init.edit(content=f"{member} wasn't brave enough to play")
        await init.delete()
        menu = BoardMenu(
            (ctx.author.id, ctx.author.display_name),
            (member.id, member.display_name),
            await ctx.embed_requested(),
            clear_reactions_after=True,
        )
        await menu.start(ctx)