import contextlib
from typing import Optional

import discord

from redbot.core import commands
from redbot.core.commands.help import HelpSettings
from redbot.core.utils.menus import (menu, next_page, prev_page,
                                     start_adding_reactions)

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
    if len(pages) <= 1:
        controls.pop("\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}", None)
        controls.pop("\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}", None)
    return await menu(ctx, pages, controls, message=message, page=0, timeout=timeout)


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
    if len(pages) > 1:
        controls["\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}"] = prev_page
        controls["\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}"] = next_page
        start_adding_reactions(
            message,
            [
                "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
                "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}",
            ],
        )
    return await menu(ctx, pages, controls, message=message, page=0, timeout=timeout)


class CategoryConvert(commands.Converter):
    async def convert(self, ctx, value: str):
        category = get_category(value)
        if category is not None:
            return category
        raise commands.BadArgument()