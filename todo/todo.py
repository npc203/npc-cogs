import asyncio
from typing import Literal

import discord

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import start_adding_reactions
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
        self.config.register_user(**{"todos": []})

    @commands.group()
    async def todo(self, ctx):
        """Contains a list of commands to set and retrieve todo tasks"""

    @todo.command()
    async def add(self, ctx, *, task: str):
        """Add a new task to your todo list"""
        async with self.config.user(ctx.author).todos() as todos:
            todo_id = len(todos)
            todos.append(task)
        await ctx.send(
            f"Your todo has been added successfully with the id: **{todo_id}**"
        )

    @todo.command(name="list")
    async def list_todos(self, ctx):
        """List all your todos"""
        todos = await self.config.user(ctx.author).todos()
        if todos:
            for page in pagify(
                box("\n".join([f"{i} - {x}" for i, x in enumerate(todos)]))
            ):
                await ctx.send(page)
            return
        await ctx.send("Currently, you have no TODOs")

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
            "Succesfully removed:\n"
            + "\n".join([f"{i}. {x}" for i, x in enumerate(removed, 1)]),
            page_length=1970,
        ):
            await ctx.send(page)

    @todo.command()
    async def removeall(self, ctx, *indices: int):
        """Remove your todo tasks, supports multiple id removals as well\n eg:[p]todo remove 1 2 3"""
        msg = await ctx.send("Are you sure do you want to remove all of your todos?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await ctx.bot.wait_for("reaction_add", check=pred)
        except asyncio.TimeoutError:
            pass
        if pred.result is True:
            await self.config.user(ctx.author).todos.set([])
            await ctx.send("Successfully removed all your TODOs")
        else:
            await ctx.send("Cancelled.")

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
