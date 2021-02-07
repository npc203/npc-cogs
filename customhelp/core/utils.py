# This contains a bunch of menu utils
from copy import copy

import discord

from redbot.core import commands
from redbot.core.commands.help import HelpSettings
from redbot.core.utils.menus import menu, start_adding_reactions

from .category import GLOBAL_CATEGORIES

# From dpy server >.<
EMOJI_REGEX = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
# https://www.w3resource.com/python-exercises/re/python-re-exercise-42.php
LINK_REGEX = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"


async def home_page(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    help_settings = await HelpSettings.from_context(ctx)
    pages = await ctx.bot._help_formatter.format_bot_help(ctx, help_settings, get_pages=True)
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
    # Stop, everyday people suffer from ratelimiting.
    """
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)
    """

    # TODO sigh getting everything again, please optimise this IMP, maybe create pages on react itself?
    help_settings = await HelpSettings.from_context(ctx)
    for x in GLOBAL_CATEGORIES:
        if x.reaction == str(emoji):
            category = x
            break
    else:
        # idk maybe edge cases
        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)
    pages_new = await ctx.bot._help_formatter.format_category_help(
        ctx, category, help_settings, get_pages=True
    )
    # Menus error out if a cog in category is unloaded
    if not pages_new:
        return await menu(ctx, pages, controls, message=message, page=0, timeout=timeout)
    if len(pages_new) > 1:
        controls["\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}"] = prev_page
        controls["\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}"] = next_page
        start_adding_reactions(
            message,
            [
                "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
                "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}",
            ],
        )
    # copy is needed so that the controls don't change during emoji addition (edge case)
    return await menu(ctx, pages_new, copy(controls), message=message, page=0, timeout=timeout)


# These methods have their message.reaction.remove deleted cause of ratelimits.(from core)
async def next_page(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    if page == len(pages) - 1:
        page = 0  # Loop around to the first item
    else:
        page = page + 1
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def prev_page(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    if page == 0:
        page = len(pages) - 1  # Loop around to the last item
    else:
        page = page - 1
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)
