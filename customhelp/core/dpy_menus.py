from __future__ import annotations

from typing import Any, List, Optional, Union

import discord
from . import ARROWS, GLOBAL_CATEGORIES
import asyncio

from redbot.vendored.discord.ext import menus
from redbot.core.bot import Red

# None of the below classes are done by me, it's mostly copy paste/ edited from a piece of code
# from trusty which got circulated around to me from !nowo. All credits go to him.
# Annd phen did some epico button magic.
# Not using an AsyncIterator cause even the core help loads all the commands at once.


class ListPages(menus.ListPageSource):
    def __init__(self, pages: List[Union[discord.Embed, str]]):
        super().__init__(pages, per_page=1)

    def is_paginating(self):
        return True

    async def format_page(self, menu: menus.MenuPages, page: Union[discord.Embed, str]):
        return page


class BaseMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(
        self,
        source: menus.PageSource,
        clear_reactions_after: bool = True,
        delete_message_after: bool = False,
        timeout: int = 60,
        message: Optional[discord.Message] = None,
        page_start: int = 0,
        *,
        hmenu,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            source,
            clear_reactions_after=clear_reactions_after,
            delete_message_after=delete_message_after,
            timeout=timeout,
            message=message,
            **kwargs,
        )
        self.page_start = page_start
        self.use_reply = False
        self.hmenu = hmenu

        self.message: discord.Message
        self.bot: Red

    async def _get_kwargs_from_page(self, page):
        kwargs: dict[str, Any] = {"allowed_mentions": discord.AllowedMentions(replied_user=False)}
        value = await discord.utils.maybe_coroutine(self._source.format_page, self, page)
        if isinstance(value, dict):
            kwargs.update(value)
        elif isinstance(value, str):
            kwargs["content"] = value
        elif isinstance(value, discord.Embed):
            kwargs["embed"] = value
        return kwargs

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if self.use_reply:
            kwargs["reference"] = ctx.message.to_reference(
                fail_if_not_exists=False
            )  # sends message silently when message is deleted
        return await ctx.send(**kwargs, view=self.hmenu.menus[1])

    async def start(self, ctx, use_reply=False, channel=None, wait=False):
        await self._source._prepare_once()
        self.use_reply = use_reply
        await super().start(ctx, channel=channel, wait=wait)
        return self.message

    async def show_checked_page(self, page_number: int):
        max_pages = self._source.get_max_pages()
        try:
            if max_pages is None or page_number < max_pages and page_number >= 0:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(page_number)
            elif page_number >= max_pages:
                await self.show_page(0)
            else:
                await self.show_page(max_pages - 1)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    def reaction_check(self, payload):
        """Just extends the default reaction_check to use owner_ids"""
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in (*self.bot.owner_ids, self._author_id):
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


async def react_page(ctx, emoji, help_settings, bypass_checks=False):
    for x in GLOBAL_CATEGORIES:
        if x.reaction == emoji:
            category = x
            break
    else:
        return
    pages = await ctx.bot._help_formatter.format_category_help(
        ctx, category, help_settings, get_pages=True, bypass_checks=bypass_checks
    )
    if pages:

        async def action(menu, payload):
            await menu.change_source(ListPages(pages), payload)
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

        return menus.Button(emoji, action)
    else:
        return empty_button(emoji)


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
        self.hmenu.stop()
        await self.message.delete()

    return menus.Button(emoji, stop_pages)


def empty_button(emoji):
    async def action(self, payload):
        pass  # yeah this won't do anything apparently

    return menus.Button(emoji, action)
