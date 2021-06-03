import datetime
import itertools
import os
from types import SimpleNamespace as sp
from typing import Union

import aiohttp
import discord
import pydriller as pd
from redbot.cogs.downloader.repo_manager import Repo
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, humanize_timedelta
from redbot.vendored.discord.ext import menus


# Taken from the core help
def shorten_line(a_line: str) -> str:
    if len(a_line) < 64:  # embed max width needs to be lower
        return a_line
    return a_line[:63] + "…"


class RepoUrl(commands.Converter):
    async def convert(self, ctx, argument):
        if not argument.startswith("http"):
            return argument
        raise discord.ext.commands.BadArgument()


class GhTools(commands.Cog):
    """
    A small set of github tools focused on Downloader cog
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self._downloader = self.bot.get_cog("Downloader")
        self._path = self._downloader._repo_manager.repos_folder
        # ._repo_manager.config.repos.all()

    # Inspired from https://github.com/Rapptz/RoboDanny/blob/644e588851bccca24f220b74f0ef091c48299757/cogs/stats.py
    def format_commit(self, commit, url=None):
        short, _, desc = commit.msg.partition("\n")
        short_sha2 = commit.hash[0:6]
        commit_tz = datetime.timezone(datetime.timedelta(seconds=commit.committer_timezone))
        commit_time = commit.committer_date.astimezone(commit_tz)

        # [`hash`](url) message (offset)

        offset = humanize_timedelta(
            seconds=abs(
                commit_time.astimezone(datetime.timezone.utc).replace(
                    tzinfo=None, hour=0, minute=0, second=0, microsecond=0
                )
                - datetime.datetime.now().replace(
                    tzinfo=None, hour=0, minute=0, second=0, microsecond=0
                )
            ).total_seconds()
        )
        return (
            f"[`{short_sha2}`]({url}/commit/{commit.hash})" + shorten_line(f"{short} ({offset})"),
            desc,
        )

    # with references to core
    async def get_commit_infos(self, cog_mgr, package=None, repo=None, count=10):
        if package:
            installed, cog_installable = await self._downloader.is_installed(package)
            if installed and cog_installable.repo_name != "MISSING_REPO":
                full_path = str(self._path / cog_installable.repo_name)
                hashes = pd.git.Git(full_path).get_commits_modified_file(package)
                commits = itertools.islice(
                    pd.Repository(
                        full_path,
                        only_commits=hashes,
                        only_in_branch=cog_installable.repo.branch,
                        order="reverse",
                    ).traverse_commits(),
                    count,
                )
                return (
                    (lambda x: sp(name=x[0], value=x[1], package=package))(
                        self.format_commit(c, url=cog_installable.repo.url)
                    )
                    for c in commits
                )
        else:
            commits = itertools.islice(
                pd.Repository(
                    str(repo.folder_path),
                    only_in_branch=repo.branch,
                    order="reverse",
                ).traverse_commits(),
                count,
            )
            return (
                (lambda x: sp(name=x[0], value=x[1], repo=repo.name))(self.format_commit(c))
                for c in commits
            )

    @commands.command()
    async def commits(self, ctx, repo: Repo = None):
        if repo:
            async with ctx.typing():
                data = await self.get_commit_infos(self.bot._cog_mgr, repo=repo, count=30)
                if data:
                    pages = ResultMenu(
                        source=EmbPages(data, per_page=5, key=lambda x: x.repo),
                    )
                    await pages.start(ctx)

        else:
            await ctx.send_help()

    # TODO fix greedy int parse
    @commands.command()
    async def updates(self, ctx, *packages: str, commit_count: int = None):
        if commit_count and commit_count > 30:
            return await ctx.send("Cannot read more than 30 commits")

        if len(packages) == 1:
            data = await self.get_commit_infos(
                self.bot._cog_mgr, package=packages[0], count=10 or commit_count
            )
            if data:
                pages = ResultMenu(
                    source=EmbPages(data, per_page=5, key=lambda x: x.package),
                )
                await pages.start(ctx)
            else:
                await ctx.send("Package not found")
        else:
            async with ctx.typing():
                full_list = []
                for package in packages:
                    data = await self.get_commit_infos(
                        package, self.bot._cog_mgr, count=5 or commit_count
                    )
                    if data:
                        full_list.extend(data)
                pages = ResultMenu(
                    source=EmbPages(full_list, per_page=5, key=lambda x: x.package),
                )
                await pages.start(ctx)

    @commands.command()
    async def ghuser(self, ctx, name):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/users/{name}") as response:
                r = await response.json()
        if "message" in r:
            return await ctx.send(f"Invalid User: {name}")

        emb = discord.Embed(
            title="Github me",
            description=f"[{r['login']}]({r['html_url']})\n{r['bio']}",
            color=await ctx.embed_color(),
        )

        if r["avatar_url"]:
            emb.set_thumbnail(url=r["avatar_url"])

        b = ["updated_at", "created_at"]

        for u in b:
            if r[u]:
                r[u] = datetime.datetime.strptime(r[u], "%Y-%m-%dT%H:%M:%SZ").strftime(
                    "%a %b %d, %Y at %H:%M GMT"
                )
        a = {
            "id": "UserID",
            "name": "Display Name",
            "public_repos": "Public repos",
            "public_gists": "Public gists",
            "twitter_username": "Twitter",
            "location": "Location",
            "blog": "Blog",
            "email": "Email",
            "followers": "Followers",
            "following": "Following",
            "public_repos": "Public Repos",
            "created_at": "Created On",
            "updated_at": "Last Updated",
        }
        for x, value in a.items():
            if r[x]:
                emb.add_field(name=value, value=r[x], inline=True)
        await ctx.send(embed=emb)


class EmbPages(menus.GroupByPageSource):
    async def format_page(self, menu, entry):
        emb = discord.Embed(title=entry.key + " Commits", color=await menu.ctx.embed_color())
        desc = "".join(
            thing.name + "\n" + (box(thing.value.strip()) + "\n" if thing.value else "")
            for thing in entry.items
        )

        emb.description = desc
        emb.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return emb


# Thanks fixator https://github.com/fixator10/Fixator10-Cogs/blob/V3.leveler_abc/leveler/menus/top.py
class ResultMenu(menus.MenuPages, inherit_buttons=False):
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
