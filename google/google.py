import functools
import urllib
from collections import namedtuple
from typing import Literal

import aiohttp
import discord
import html2text
from bs4 import BeautifulSoup

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import pagify

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Google(commands.Cog):
    """
    A simple google search
    A fair bit of querying stuff is taken from  Kowlin's cog - https://github.com/Kowlin/refactored-cogs
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.command()
    async def google(self, ctx, *, query: str = None):
        """Search in google from discord
        Note: This cog is done, with major references to Kowlin's cog - https://github.com/Kowlin/refactored-cogs"""
        if not query:
            await ctx.send("Please enter something to search")
        else:
            async with ctx.typing():
                if response := await self.get_result(query):
                    pages = []
                    groups = [
                        response[0][n : n + 3] for n in range(0, len(response[0]), 3)
                    ]
                    for num, group in enumerate(groups, 1):
                        emb = discord.Embed(title=f"Google Search: {query[:50]}...")
                        for result in group:
                            emb.add_field(
                                name=f"{result.title}",
                                value=f"[{result.url}]({result.url})\n"
                                if result.url
                                else "" f"{result.desc}"[:1024],
                                inline=False,
                            )
                        emb.description = f"Page {num} of {len(groups)}"
                        emb.set_footer(text=response[1])
                        pages.append(emb)
                else:
                    await ctx.send("No result")
                    return
            await menus.menu(ctx, pages, controls=menus.DEFAULT_CONTROLS)

    def parser(self, text):
        """My bad logic for scraping"""
        soup = BeautifulSoup(text, features="html.parser")
        s = namedtuple("searchres", "url title desc")
        final = []
        stats = html2text.html2text(str(soup.find("div", id="result-stats")))
        if card := soup.find("div", class_="g mnr-c g-blk"):
            if desc := card.find("span", class_="hgKElc"):
                final.append(
                    s(None, "Google Info Card:", html2text.html2text(str(desc)))
                )
        for res in soup.findAll("div", class_="g"):
            if name := res.find("div", class_="yuRUbf"):
                url = name.a["href"]
                if title := name.find("h3", "LC20lb DKV0Md"):
                    title = title.text
                else:
                    title = url
            else:
                title = None
            if desc := res.find("div", class_="IsZvec"):
                if remove := desc.find("span", class_="f"):
                    remove.decompose()
                desc = html2text.html2text(str(desc.find("span", class_="aCOpRe")))
            else:
                desc = "Not found"
            if title:
                final.append(s(url, title, desc))
        return final, stats

    async def get_result(self, query):
        """Fetch the data"""
        # TODO make this fetching a little better
        encoded = urllib.parse.quote_plus(query, encoding="utf-8", errors="replace")
        url = "https://www.google.com/search?q="
        options = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url + encoded, headers=options) as resp:
                text = await resp.text()
        prep = functools.partial(self.parser, text)
        res = await self.bot.loop.run_in_executor(None, prep)
        return res
