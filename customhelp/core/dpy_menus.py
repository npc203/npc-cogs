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
        page = self.hmenu.pages[0]
        kwargs = self.hmenu._get_kwargs_from_page(page)
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


async def react_page(category_obj, pages):
    async def action(menu: BaseMenu, payload):
        await menu.hmenu.category_react_action(menu.ctx, menu.message, category_obj.name)

    return menus.Button(category_obj.reaction, action)


async def arrow_react(arrow_obj):
    async def action(menu: BaseMenu, payload):
        await menu.hmenu.arrow_emoji_button[arrow_obj.name]()

    return menus.Button(arrow_obj.emoji, action)


# TODO fix this lol
async def home_page(emoji, help_settings):
    async def action(menu, payload):
        menu.hmenu.change_source(pages)
        if len(pages) == 1 and ARROWS["left"].name in map(str, menu._buttons.keys()):
            menu.add_button(empty_button(ARROWS["left"]))
            menu.add_button(empty_button(ARROWS["right"]))

    return menus.Button(emoji, action)
