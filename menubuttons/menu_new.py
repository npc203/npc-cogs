import asyncio
import functools
from typing import List, Union

import discord
from redbot.core import commands
from redbot.core.utils.menus import start_adding_reactions


class MenuMixin:
    def _get_emoji(self, button):  # InteractionButton, can't type hint this ;c
        emoji_string = button.custom_id[len(self.custom_id) + 1 :]

    def send_with_buttons(self, button):
        pass

    def create_proper_controls(self, controls):
        """Returns a Dict[Arrow,function]"""

    async def new_button_menu(
        self,
        ctx: commands.Context,
        pages: Union[List[str], List[discord.Embed]],
        controls: dict,
        message: discord.Message = None,
        page: int = 0,
        timeout: float = 30.0,
    ):
        """Same red menu but supports buttons"""
        if not isinstance(pages[0], (discord.Embed, str)):
            raise RuntimeError("Pages must be of type discord.Embed or str")
        if not all(isinstance(x, discord.Embed) for x in pages) and not all(
            isinstance(x, str) for x in pages
        ):
            raise RuntimeError("All pages must be of the same type")
        for key, value in controls.items():
            maybe_coro = value
            if isinstance(value, functools.partial):
                maybe_coro = value.func
            if not asyncio.iscoroutinefunction(maybe_coro):
                raise RuntimeError("Function must be a coroutine")
        current_page = pages[page]

        if not message:
            if isinstance(current_page, discord.Embed):
                message = await ctx.send(embed=current_page)
            else:
                message = await ctx.send(current_page)
        else:
            try:
                if isinstance(current_page, discord.Embed):
                    await message.edit(embed=current_page)
                else:
                    await message.edit(content=current_page)
            except discord.NotFound:
                return

        try:
            predicate = (
                lambda payload: not ctx.author.bot
                and message.id == payload.message.id
                and payload.custom_id in tuple(controls.keys())  # TODO
            )
            payload = await ctx.bot.wait_for(
                "button_interaction", check=predicate, timeout=timeout
            )
        except asyncio.TimeoutError:
            if not ctx.me:
                return
            try:
                if message.channel.permissions_for(ctx.me).manage_messages:
                    await message.clear_reactions()
                else:
                    raise RuntimeError
            except (discord.Forbidden, RuntimeError):  # cannot remove all reactions
                for key in controls.keys():
                    try:
                        await message.remove_reaction(key, ctx.bot.user)
                    except discord.Forbidden:
                        return
                    except discord.HTTPException:
                        pass
            except discord.NotFound:
                return
        else:
            return await controls[payload.custom_id](
                ctx, pages, controls, message, page, timeout, react.emoji
            )
