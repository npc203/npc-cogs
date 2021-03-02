import asyncio
from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import (DEFAULT_CONTROLS, menu,
                                     start_adding_reactions)
from redbot.core.utils.predicates import ReactionPredicate

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Todo(commands.Cog):
    """
    A simple todo list
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=6732102719277,
            force_registration=True,
        )
        self.config.register_user(todos=[])
        self.config.register_global(embeds=True, menus=True)

    @commands.group(invoke_without_command=True)
    async def todo(self, ctx, id_: int):
        """Contains a list of commands to set and retrieve todo tasks \n Use todo <id> to get a specific todo"""
        todos = await self.config.user(ctx.author).todos()
        if -len(todos) < id_ < len(todos):
            await ctx.send(todos[id_])
        else:
            await ctx.send(f"Invalid ID: {id_}")

    @commands.is_owner()
    @todo.command()
    async def embedset(self, ctx, toggle: bool):
        """Enable/Disable embeds for todos"""
        if toggle:
            await self.config.embeds.set(True)
        else:
            await self.config.embeds.set(False)
        await ctx.send(f'Sucessfully {"Enabled" if toggle else "Disabled"} embeds for todo lists')

    @commands.is_owner()
    @todo.command()
    async def menuset(self, ctx, toggle: bool):
        """Enable/Disable menus for todos"""
        if toggle:
            await self.config.menus.set(True)
        else:
            await self.config.menus.set(False)
        await ctx.send(f'Sucessfully {"Enabled" if toggle else "Disabled"} menus for todo lists')

    @todo.command()
    async def add(self, ctx, *, task: str):
        """Add a new task to your todo list, DO NOT STORE SENSITIVE INFO HERE"""
        async with self.config.user(ctx.author).todos() as todos:
            todo_id = len(todos)
            todos.append(task)
        await ctx.send(f"Your todo has been added successfully with the id: **{todo_id}**")

    @todo.command(name="list")
    async def list_todos(self, ctx):
        """List all your todos"""
        todos = await self.config.user(ctx.author).todos()
        if not todos:
            await ctx.send("Currently, you have no TODOs")
        else:
            todo_text = "\n".join([f"{i} - {x}" for i, x in enumerate(todos)])
            if await self.config.embeds():
                pagified = tuple(pagify(todo_text, page_length=1004, shorten_by=0))
                # embeds and menus
                if await self.config.menus():
                    emb_pages = [
                        discord.Embed(
                            title="Your TODO List",
                            description=f"Page:{num}/{len(pagified)}\n\n{page}",
                        )
                        for num, page in enumerate(pagified, 1)
                    ]
                    await menu(ctx, emb_pages, DEFAULT_CONTROLS, timeout=120)
                # embeds and not menus
                else:
                    for page in pagified:
                        await ctx.send(
                            embed=discord.Embed(
                                title="Your TODO List",
                                description=page,
                            )
                        )
            else:
                pagified = tuple(pagify(todo_text))
                # not embeds and menus
                if await self.config.menus():
                    await menu(ctx, pagified, DEFAULT_CONTROLS, timeout=120)
                # not embeds and not menus
                else:
                    for page in pagified:
                        await ctx.send(page)

    @todo.command(aliases=["rearrange"])
    async def reorder(self, ctx, from_: int, to: int):
        async with self.config.user(ctx.author).todos() as todos:
            if -len(todos) < from_ < len(todos):
                if -len(todos) < to < len(todos):
                    todos[from_], todos[to] = todos[to], todos[from_]
                    await ctx.send(f"Sucessfully swapped {from_} and {to}")
                else:
                    await ctx.send(f"Invaild ID: {to}")
            else:
                await ctx.send(f"Invaild ID: {from_}")

    @todo.command()
    async def remove(self, ctx, *indices: int):
        """Remove your todo tasks, supports multiple id removals as well\n eg:[p]todo remove 1 2 3"""
        if len(indices) == 1:
            async with self.config.user(ctx.author).todos() as todos:
                x = todos.pop(indices[0])
                await ctx.send(f"Succesfully removed: {x}")
            return

        removed = []
        async with self.config.user(ctx.author).todos() as todos:
            temp = []
            for j, i in enumerate(todos):
                if j not in indices:
                    temp.append(i)
                else:
                    removed.append(i)
            todos[:] = temp
        for page in pagify(
            "Succesfully removed:\n" + "\n".join([f"{i}. {x}" for i, x in enumerate(removed, 1)]),
            page_length=1970,
        ):
            await ctx.send(page)

    @todo.command()
    async def removeall(self, ctx, *indices: int):
        """Remove all your todo tasks"""
        msg = await ctx.send("Are you sure do you want to remove all of your todos?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await ctx.bot.wait_for("reaction_add", check=pred)
        except asyncio.TimeoutError:
            pass
        if pred.result is True:
            await self.config.user_from_id(ctx.author.id).clear()
            await ctx.send("Successfully removed all your TODOs")
        else:
            await ctx.send("Cancelled.")

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # should I add anything more here?
        await self.config.user_from_id(user_id).clear()
