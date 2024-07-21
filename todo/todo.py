import asyncio
import random
from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
from redbot.vendored.discord.ext import menus
from redbot_ext_menus import ViewMenuPages

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
        self.config.register_global(menus=True)

    @commands.group(invoke_without_command=True)
    async def todo(self, ctx, id_: int):
        """Contains a list of commands to set and retrieve todo tasks \n Use todo <id> to get a specific todo"""
        todos = await self.config.user(ctx.author).todos()
        try:
            if isinstance(todos[id_], list):
                await ctx.send(todos[id_][1])
            else:
                await ctx.send(todos[id_])
        except IndexError:
            await ctx.send(f"Invalid ID: {id_}")

    @commands.is_owner()
    @todo.command()
    async def menuset(self, ctx, toggle: bool):
        """Enable/Disable menus for todos"""
        if toggle:
            await self.config.menus.set(True)
        else:
            await self.config.menus.set(False)
        await ctx.send(f'Successfully {"enabled" if toggle else "disabled"} menus for todo lists')

    @todo.command()
    async def add(self, ctx, *, task: str):
        """Add a new task to your todo list, DO NOT STORE SENSITIVE INFO HERE"""
        async with self.config.user(ctx.author).todos() as todos:
            todo_id = len(todos)
            todos.append([ctx.message.jump_url, task])  # using a list to support future todo edit
        await ctx.send(f"Your todo has been added successfully with the id: **{todo_id}**")

    @todo.command(aliases=["r", "rand"])
    async def random(self, ctx):
        """Displays a random todo from your todo list"""
        todos = await self.config.user(ctx.author).todos()
        try:
            id_ = random.randint(0, len(todos) - 1)
        except ValueError:
            return await ctx.send("You have no more todos.")
        if isinstance(todos[id_], list):
            await ctx.send(todos[id_][1])
        else:
            await ctx.send(todos[id_])

    @todo.command()
    async def edit(self, ctx, index: int, *, task: str):
        """Edit a todo quickly"""
        async with self.config.user(ctx.author).todos() as todos:
            try:
                old = todos[index][1] if isinstance(todos[index], list) else todos[index]
                todos[index] = [ctx.message.jump_url, task]
                await ctx.send_interactive(
                    pagify(
                        f"Sucessfully edited Todo ID: {index}\n**from:**\n{old}\n**to:**\n{task}"
                    )
                )
            except IndexError:
                await ctx.send(f"Invalid Todo ID: {index}")

    @todo.command(name="list")
    async def list_todos(self, ctx):
        """List all your todos"""
        todos = await self.config.user(ctx.author).todos()
        if not todos:
            await ctx.send("Currently, you have no TODOs")
        else:
            todo_text = ""
            if await ctx.embed_requested():
                for i, x in enumerate(todos):
                    if isinstance(x, list):
                        todo_text += f"[{i}]({x[0]}). {x[1]}\n"
                    else:
                        todo_text += f"{i}. {x}\n"
                pagified = tuple(pagify(todo_text, page_length=2048, shorten_by=0))
                # embeds and menus
                if await self.config.menus():
                    emb_pages = [
                        discord.Embed(
                            title="Your TODO List",
                            description=page,
                            color=await ctx.embed_color(),
                        ).set_footer(text=f"Page: {num}/{len(pagified)}")
                        for num, page in enumerate(pagified, 1)
                    ]
                    await ResultMenu(source=Source(emb_pages, per_page=1)).start(ctx)
                # embeds and not menus
                else:
                    for num, page in enumerate(pagified, 1):
                        await ctx.send(
                            embed=discord.Embed(
                                title="Your TODO List",
                                description=page,
                                color=await ctx.embed_color(),
                            ).set_footer(text=f"Page: {num}/{len(pagified)}")
                        )
            else:
                for i, x in enumerate(todos):
                    todo_text += f"{i}. {x[1]}\n" if isinstance(x, list) else f"{i}. {x}\n"
                pagified = tuple(pagify(todo_text))
                # not embeds and menus
                if await self.config.menus():
                    await ResultMenu(source=Source(pagified, per_page=1)).start(ctx)
                # not embeds and not menus
                else:
                    for page in pagified:
                        await ctx.send(page)

    @todo.command(aliases=["rearrange"])
    async def reorder(self, ctx, from_: int, to: int):
        """Reorder your todos using IDs to swap them"""
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
    async def search(self, ctx, *, text):
        """Quick search in your todos to find stuff fast"""
        no_case = text.lower()
        todos = await self.config.user(ctx.author).todos()
        async with ctx.typing():
            results = []
            for ind in range(len(todos)):
                x = todos[ind][1] if isinstance(todos[ind], list) else todos[ind]
                if no_case in x.lower():
                    results.append(f"**{ind}**. {x}")
            if results:
                await ctx.send_interactive(
                    pagify(f"Search results for {text}:\n" + "\n".join(results))
                )
            else:
                await ctx.send(f"No results found for {text}")

    @todo.command(aliases=["delete"])
    async def remove(self, ctx, *indices: int):
        """Remove your todo tasks, supports multiple id removals as well\n eg:[p]todo remove 1 2 3"""
        todos = await self.config.user(ctx.author).todos()
        if len(indices) == 1:
            try:
                x = todos.pop(indices[0])
                await self.config.user(ctx.author).todos.set(todos)
                await ctx.send_interactive(
                    pagify(f"Succesfully removed: {x[1] if isinstance(x,list) else x}")
                )
            except IndexError:
                await ctx.send(f"Invalid ID: {indices[0]}")
        else:
            removed = []
            temp = []
            removed_inds = []
            for j, i in enumerate(todos):
                if j not in indices:
                    temp.append(i)
                else:
                    removed.append(i)
                    removed_inds.append(j)
            await self.config.user(ctx.author).todos.set(temp)
            if removed:
                await ctx.send_interactive(
                    pagify(
                        (
                            f"Invalid IDs:{', '.join(str(i) for i in indices if i not in removed_inds)} \n"
                            if len(removed) != len(indices)
                            else ""
                        )
                        + "Succesfully removed:\n"
                        + "\n".join(
                            f"{i}. {x[1] if isinstance(x,list) else x}"
                            for i, x in enumerate(removed, 1)
                        ),
                    )
                )
            else:
                await ctx.send(f"Invalid IDs: {', '.join(map(str,indices))}")

    @todo.command(aliases=["clear"])
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


# Dpy menus
class Source(menus.ListPageSource):
    async def format_page(self, menu, embeds):
        return embeds


# Thanks fixator https://github.com/fixator10/Fixator10-Cogs/blob/V3.leveler_abc/leveler/menus/top.py
class ResultMenu(ViewMenuPages, inherit_buttons=False):
    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            timeout=60,
            clear_reactions_after=True,
            delete_message_after=True,
        )

    def _skip_double_triangle_buttons(self):
        return super()._skip_double_triangle_buttons()

    async def finalize(self, timed_out):
        """|coro|
        A coroutine that is called when the menu loop has completed
        its run. This is useful if some asynchronous clean-up is
        required after the fact.
        Parameters
        --------------
        timed_out: :class:`bool`
            Whether the menu completed due to timing out.
        """
        if timed_out and self.delete_message_after:
            self.delete_message_after = False

    @menus.button(
        "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.First(0),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_first_page(self, payload):
        """go to the first page"""
        await self.show_page(0)

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f", position=menus.First(1))
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        if self.current_page == 0:
            await self.show_page(self._source.get_max_pages() - 1)
        else:
            await self.show_checked_page(self.current_page - 1)

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f", position=menus.Last(0))
    async def go_to_next_page(self, payload):
        """go to the next page"""
        if self.current_page == self._source.get_max_pages() - 1:
            await self.show_page(0)
        else:
            await self.show_checked_page(self.current_page + 1)

    @menus.button(
        "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.Last(1),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_last_page(self, payload):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(self._source.get_max_pages() - 1)

    @menus.button("\N{CROSS MARK}", position=menus.First(2))
    async def stop_pages(self, payload) -> None:
        self.stop()
