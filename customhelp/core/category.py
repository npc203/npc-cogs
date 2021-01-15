from typing import Optional
from redbot.core import commands
import contextlib
import discord
from redbot.core.utils.menus import menu
from redbot.core.commands.help import HelpSettings

GLOBAL_CATEGORIES = []


class Category:
    def __init__(
        self,
        name: str,
        desc: str,
        cogs: list,
        reaction: str = None,
        long_desc: str = None,
    ):
        self.name = name
        self.desc = desc
        self.long_desc = long_desc
        self.cogs = cogs
        self.reaction = reaction

    def __eq__(self, item):
        return item == self.name


# Helpers
def get_category(category: str) -> Optional[Category]:
    for x in GLOBAL_CATEGORIES:
        if x.name == category:
            return x


async def home_page(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)

    help_settings = await HelpSettings.from_context(ctx)
    pages = await ctx.bot._help_formatter.format_bot_help(
        ctx, help_settings, get_pages=True
    )
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


# TODO
async def react_page(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)

    # TODO sigh getting everything again, please optimise this IMP, maybe create pages on react itself?
    help_settings = await HelpSettings.from_context(ctx)
    for x in GLOBAL_CATEGORIES:
        if x.reaction == emoji:
            category = x
            break
    pages = await ctx.bot._help_formatter.format_category_help(
        ctx, category, help_settings, get_pages=True
    )
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


class CategoryConvert(commands.Converter):
    async def convert(self, ctx, value: str):
        category = get_category(value)
        if category is not None:
            return category
        raise commands.BadArgument()
