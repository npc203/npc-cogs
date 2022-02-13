# This contains a bunch of utils

import asyncio

import discord
from redbot.core.utils.chat_formatting import humanize_timedelta

from . import ARROWS, GLOBAL_CATEGORIES
from .dpy_menus import ListPages, menus

# From dpy server >.<
EMOJI_REGEX = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
# https://www.w3resource.com/python-exercises/re/python-re-exercise-42.php
LINK_REGEX = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"


def emoji_converter(bot, emoji):
    """General emoji converter"""
    # TODO find a way to detect unicode emojis properly
    if not emoji:
        return
    if isinstance(emoji, int) or emoji.isdigit():
        return bot.get_emoji(int(emoji))
    emoji = emoji.strip()
    return emoji


# Taken from the core help as well :)
def shorten_line(a_line: str) -> str:
    if len(a_line) < 70:  # embed max width needs to be lower
        return a_line
    return a_line[:67] + "..."


# Add permissions
def get_perms(command):
    final_perms = ""
    neat_format = lambda x: " ".join(i.capitalize() for i in x.replace("_", " ").split())

    user_perms = []
    if perms := getattr(command.requires, "user_perms"):
        user_perms.extend(neat_format(i) for i, j in perms if j)
    if perms := command.requires.privilege_level:
        if perms.name != "NONE":
            user_perms.append(neat_format(perms.name))

    if user_perms:
        final_perms += "User Permission(s): " + ", ".join(user_perms) + "\n"

    if perms := getattr(command.requires, "bot_perms"):
        if perms_list := ", ".join(neat_format(i) for i, j in perms if j):
            final_perms += "Bot Permission(s): " + perms_list

    return final_perms


# Add cooldowns
def get_cooldowns(command):
    cooldowns = []
    if s := command._buckets._cooldown:
        txt = f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)}"
        try:
            txt += f" per {s.type.name.capitalize()}"
        # This is to avoid custom bucketype erroring out stuff (eg:licenseinfo)
        except AttributeError:
            pass
        cooldowns.append(txt)

    if s := command._max_concurrency:
        cooldowns.append(f"Max concurrent uses: {s.number} per {s.per.name.capitalize()}")

    return cooldowns


# Add aliases
def get_aliases(command, original):
    if alias := list(command.aliases):
        if original in alias:
            alias.remove(original)
            alias.append(command.name)
        return alias


# dpy menus helpers, taken from dpy menus :D
def _skip_single_arrows(self):
    max_pages = self._source.get_max_pages()
    return max_pages == 1


def _skip_double_triangle_buttons(self):
    max_pages = self._source.get_max_pages()
    if max_pages is None:
        return True
    return max_pages <= 2


async def react_page(ctx, emoji, help_settings, bypass_checks=False):
    for x in GLOBAL_CATEGORIES:
        if x.reaction == emoji:
            category = x
            break
    pages = await ctx.bot._help_formatter.format_category_help(
        ctx, category, help_settings, get_pages=True, bypass_checks=bypass_checks
    )
    if pages:

        async def action(menu, payload):
            await menu.change_source(ListPages(pages), payload)
            if len(pages) == 1:
                # If any one button is present, disable it's functionality cause its a 1 page menu.
                if ARROWS["left"] in map(str, menu._buttons.keys()):
                    menu.add_button(empty_button(ARROWS["left"]))
                    menu.add_button(empty_button(ARROWS["right"]))
            else:
                asyncio.create_task(
                    menu.add_button(prev_page(ARROWS["left"]), react=True, interaction=payload)
                )
                asyncio.create_task(
                    menu.add_button(next_page(ARROWS["right"]), react=True, interaction=payload)
                )

        return menus.Button(emoji, action)
    else:
        return empty_button(emoji)


async def home_page(ctx, emoji, help_settings):
    pages = await ctx.bot._help_formatter.format_bot_help(ctx, help_settings, get_pages=True)
    if pages:

        async def action(menu, payload):
            await menu.change_source(ListPages(pages), payload)
            if len(pages) == 1 and ARROWS["left"] in map(str, menu._buttons.keys()):
                menu.add_button(empty_button(ARROWS["left"]))
                menu.add_button(empty_button(ARROWS["right"]))

        return menus.Button(emoji, action)
    else:
        return empty_button(emoji)


def first_page(emoji):
    async def go_to_first_page(self, payload):
        """go to the first page"""
        await self.show_page(0, payload)

    return menus.Button(
        emoji, go_to_first_page, position=menus.First(), skip_if=_skip_double_triangle_buttons
    )


def last_page(emoji):
    async def go_to_last_page(self, payload):
        """go to the last page"""
        await self.show_page(self._source.get_max_pages() - 1, payload)

    return menus.Button(emoji, go_to_last_page, skip_if=_skip_double_triangle_buttons)


def prev_page(emoji):
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        await self.show_checked_page(self.current_page - 1, payload)

    return menus.Button(emoji, go_to_previous_page, skip_if=_skip_single_arrows)


def next_page(emoji):
    async def go_to_next_page(self, payload):
        """go to the next page"""
        await self.show_checked_page(self.current_page + 1, payload)

    return menus.Button(emoji, go_to_next_page, skip_if=_skip_single_arrows)


def close_menu(emoji):
    async def stop_pages(self, payload: discord.RawReactionActionEvent) -> None:
        """stops the pagination session."""
        self.stop()
        await self.message.delete()

    return menus.Button(emoji, stop_pages)


def empty_button(emoji):
    async def action(self, payload):
        pass  # yeah this won't do anything apparently

    return menus.Button(emoji, action)
