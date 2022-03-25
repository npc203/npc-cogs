from __future__ import annotations

import asyncio
from typing import Any, List, Optional, Union

import discord
from redbot.core.bot import Red
from redbot.vendored.discord.ext import menus

import customhelp.core.base_help as base_help

from . import ARROWS, GLOBAL_CATEGORIES


class BaseMenu(menus.Menu):
    def __init__(
        self,
        message: Optional[discord.Message] = None,
        *,
        hmenu: base_help.HybridMenus,
    ) -> None:
        super().__init__(message=message, timeout=hmenu.settings["timeout"])
        self.use_reply = hmenu.settings["replies"]
        self.hmenu = hmenu

        self.message: discord.Message
        self.bot: Red

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if self.use_reply:
            kwargs["reference"] = ctx.message.to_reference(
                fail_if_not_exists=False
            )  # sends message silently when message is deleted
        return await ctx.send(**kwargs, view=self.hmenu.menus[1])

    async def start(self, ctx, channel=None, wait=False):
        await super().start(ctx, channel=channel, wait=wait)
        return self.message

    def reaction_check(self, payload):
        """Just extends the default reaction_check to use owner_ids"""
        if payload.message_id != self.message.id:
            return False
        if self.bot.owner_ids and payload.user_id not in (*self.bot.owner_ids, self._author_id):
            return False
        return payload.emoji in self.buttons


# dpy menus helpers, taken from dpy menus :D
def _skip_single_arrows(self):
    max_pages = self._source.get_max_pages()
    return max_pages == 1


def _skip_double_triangle_buttons(self):
    max_pages = self._source.get_max_pages()
    if max_pages is None:
        return True
    return max_pages <= 2


async def react_page(ctx, category_obj, help_settings, bypass_checks=False):
    pages = await ctx.bot._help_formatter.format_category_help(
        ctx, category_obj, help_settings, get_pages=True, bypass_checks=bypass_checks
    )
    if pages:

        async def action(menu, payload):
            await menu.change_source(payload)
            if len(pages) == 1:
                # If any one button is present, disable it's functionality cause its a 1 page menu.
                if ARROWS["left"].name in map(str, menu._buttons.keys()):
                    menu.add_button(empty_button(ARROWS["left"]))
                    menu.add_button(empty_button(ARROWS["right"]))
            else:
                asyncio.create_task(
                    menu.add_button(prev_page(ARROWS["left"]), react=True, interaction=payload)
                )
                asyncio.create_task(
                    menu.add_button(next_page(ARROWS["right"]), react=True, interaction=payload)
                )

        return menus.Button(category_obj.reaction, action)
    else:
        return empty_button(category_obj.reaction)


async def home_page(ctx, emoji, help_settings):
    pages = await ctx.bot._help_formatter.format_bot_help(ctx, help_settings, get_pages=True)
    if pages:

        async def action(menu, payload):
            await menu.change_source(ListPages(pages), payload)
            if len(pages) == 1 and ARROWS["left"].name in map(str, menu._buttons.keys()):
                menu.add_button(empty_button(ARROWS["left"]))
                menu.add_button(empty_button(ARROWS["right"]))

        return menus.Button(emoji, action)
    else:
        return empty_button(emoji)


def first_page(emoji):
    async def go_to_first_page(self, payload):
        """go to the first page"""
        await self.show_page(0)

    return menus.Button(emoji, go_to_first_page, position=menus.First())


def last_page(emoji):
    async def go_to_last_page(self, payload):
        """go to the last page"""
        await self.show_page(self._source.get_max_pages() - 1)

    return menus.Button(emoji, go_to_last_page)


def prev_page(emoji):
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        await self.show_checked_page(self.current_page - 1)

    return menus.Button(
        emoji,
        go_to_previous_page,
    )


def next_page(emoji):
    async def go_to_next_page(self, payload):
        """go to the next page"""
        await self.show_checked_page(self.current_page + 1)

    return menus.Button(
        emoji,
        go_to_next_page,
    )


def close_menu(emoji):
    async def stop_pages(self, payload: discord.RawReactionActionEvent) -> None:
        """stops the pagination session."""
        self.hmenu.stop()
        await self.message.delete()

    return menus.Button(emoji, stop_pages)


def empty_button(emoji):
    async def action(self, payload):
        pass  # yeah this won't do anything apparently

    return menus.Button(emoji, action)
