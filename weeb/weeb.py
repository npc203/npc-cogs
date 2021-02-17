import contextlib
from random import choice

import discord
from discord import NotFound
from redbot.core import commands, data_manager


class Weeb(commands.Cog):
    """Set of weeby commands to show your otaku-ness\n
    you can use 'c' as an additional argument for deleting your message
    Eg: `[p]uwu c`"""

    def __init__(self, bot):
        self.bot = bot
        with open(data_manager.bundled_data_path(self) / "owo.txt", "r", encoding="utf8") as f:
            self.owo = f.read().splitlines()
        with open(data_manager.bundled_data_path(self) / "uwu.txt", "r", encoding="utf8") as f:
            self.uwu = f.read().splitlines()
        with open(data_manager.bundled_data_path(self) / "xwx.txt", "r", encoding="utf8") as f:
            self.xwx = f.read().splitlines()

    @commands.command()
    async def uwu(self, ctx, option: str = None):
        """Replies with UwU variant emoticons\n
        `[p]uwu c` - deletes your message"""
        if option == "c":
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                with contextlib.suppress(NotFound):
                    await ctx.message.delete()
            else:
                raise commands.BotMissingPermissions(discord.Permissions(manage_messages=True))
        await ctx.send(choice(self.uwu))

    @commands.command()
    async def owo(self, ctx, option: str = None):
        """Replies with OwO variant emoticons
        `[p]owo c` - deletes your message"""
        if option == "c":
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                with contextlib.suppress(NotFound):
                    await ctx.message.delete()
            else:
                raise commands.BotMissingPermissions(discord.Permissions(manage_messages=True))
        await ctx.send(choice(self.owo))

    @commands.command()
    async def xwx(self, ctx, option: str = None):
        """Replies with flower girl/yandere girl
        `[p]xwx c` - deletes your message"""
        if option == "c":
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                with contextlib.suppress(NotFound):
                    await ctx.message.delete()
            else:
                raise commands.BotMissingPermissions(discord.Permissions(manage_messages=True))
        await ctx.send(choice(self.xwx))

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
