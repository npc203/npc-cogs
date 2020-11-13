from redbot.core import commands, data_manager
import discord
from random import choice


class Weeb(commands.Cog):
    """Set of weeby commands to show your otaku-ness\n
    you can also use 'c' as an additional argument for deleting your message
    Eg: `[p]uwu c`"""

    def __init__(self, bot):
        self.bot = bot
        with open(
            data_manager.bundled_data_path(self) / "owo.txt", "r", encoding="utf8"
        ) as f:
            self.owo = f.read().splitlines()
        with open(
            data_manager.bundled_data_path(self) / "uwu.txt", "r", encoding="utf8"
        ) as f:
            self.uwu = f.read().splitlines()
        with open(
            data_manager.bundled_data_path(self) / "xwx.txt", "r", encoding="utf8"
        ) as f:
            self.xwx = f.read().splitlines()

    @commands.command(usage="[c]")
    async def uwu(self, ctx, option: str = None):
        """Replies with UwU variant emoticons\n
        `[p]uwu c` - deletes your message"""
        if option == "c":
            await ctx.message.delete()
        await ctx.send(choice(self.uwu))

    @commands.command(usage="[c]")
    async def owo(self, ctx, option: str = None):
        """Replies with OwO variant emoticons
        `[p]owo c` - deletes your message"""
        if option == "c":
            await ctx.message.delete()
        await ctx.send(choice(self.owo))

    @commands.command(usage="[c]")
    async def xwx(self, ctx, option: str = None):
        """Replies with flower girl/yandere girl\n
        `[p]xwx c` - deletes your message"""
        if option == "c":
            await ctx.message.delete()
        await ctx.send(choice(self.xwx))

    async def cog_command_error(self, ctx, error):
        if hasattr(error, "original") and isinstance(
            error.original, discord.errors.Forbidden
        ):
            await ctx.send(
                'I require the "Manage Messages" permission to execute that command.'
            )
        else:
            await self.bot.on_command_error(ctx, error, unhandled_by_cog=True)

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
