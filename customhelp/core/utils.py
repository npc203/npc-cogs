# This contains a bunch of utils

import discord
import asyncio
from emoji import UNICODE_EMOJI_ENGLISH
from redbot.core import commands
from redbot.core.commands.help import HelpSettings
from .dpy_menus import ListPages, menus
from . import GLOBAL_CATEGORIES, ARROWS

# From dpy server >.<
EMOJI_REGEX = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
# https://www.w3resource.com/python-exercises/re/python-re-exercise-42.php
LINK_REGEX = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

# TODO find a way to detect unicode emojis properly
def emoji_converter(bot, emoji):
    """General emoji converter"""
    if not emoji:
        return
    if isinstance(emoji, int) or emoji.isdigit():
        return bot.get_emoji(int(emoji))
    emoji = emoji.strip()
    return emoji
    """
    if match := re.search(EMOJI_REGEX, emoji):
        return emoji
    else:
        return emoji
    """


# dpy menus helpers
def _skip_single_arrows(self):
    max_pages = self._source.get_max_pages()
    return max_pages == 1


async def react_page(ctx, emoji, help_settings):
    for x in GLOBAL_CATEGORIES:
        if x.reaction == emoji:
            category = x
            break
    pages = await ctx.bot._help_formatter.format_category_help(
        ctx, category, help_settings, get_pages=True
    )

    async def action(menu, payload):
        menu._source = ListPages(pages)
        asyncio.create_task(menu.add_button(prev_page(ARROWS["left"]), react=True))
        asyncio.create_task(menu.add_button(next_page(ARROWS["right"]), react=True))
        await menu.show_page(0)

    return menus.Button(emoji, action)


async def home_page(ctx, emoji, help_settings):
    pages = await ctx.bot._help_formatter.format_bot_help(ctx, help_settings, get_pages=True)

    async def action(menu, payload):
        menu._source = ListPages(pages)
        asyncio.create_task(menu.add_button(prev_page(ARROWS["left"]), react=True))
        asyncio.create_task(menu.add_button(next_page(ARROWS["right"]), react=True))
        await menu.show_page(0)

    return menus.Button(emoji, action)


def prev_page(emoji):
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        await self.show_checked_page(self.current_page - 1)

    return menus.Button(emoji, go_to_previous_page, skip_if=_skip_single_arrows)


def next_page(emoji):
    async def go_to_next_page(self, payload):
        """go to the next page"""
        await self.show_checked_page(self.current_page + 1)

    return menus.Button(emoji, go_to_next_page, skip_if=_skip_single_arrows)


def close_menu(emoji):
    async def stop_pages(self, payload: discord.RawReactionActionEvent) -> None:
        """stops the pagination session."""
        self.stop()
        await self.message.delete()

    return menus.Button(emoji, stop_pages)


def empty_button(emoji):
    async def action(x, y):
        pass

    return menus.Button(emoji, action)
