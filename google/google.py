import functools
import urllib
from collections import namedtuple

import aiohttp
import discord
import html2text
from bs4 import BeautifulSoup
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils import menus


# TODO Add optional way to use from google search api


def nsfwcheck():
    """This check is taken from Preda's NSFW cog, https://github.com/PredaaA/predacogs/blob/219e83da1e75539f8a25b7d9192e8f99d21edae9/nsfw/core.py#L206"""

    async def predicate(ctx: commands.Context):

        if not ctx.guild:
            return True
        if ctx.channel.is_nsfw():
            return True

        msg = "You can't use this command in a non-NSFW channel !"
        try:
            embed = discord.Embed(title="\N{LOCK} " + msg, color=0xAA0000)
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(msg)
        finally:
            return False

    return commands.check(predicate)


class Google(commands.Cog):
    """
    A Simple google search with image support as well
    A fair bit of querying stuff is taken from  Kowlin's cog - https://github.com/Kowlin/refactored-cogs
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def google(self, ctx, *, query: str = None):
        """Search in google from discord"""
        if not query:
            await ctx.send("Please enter something to search")
        else:
            async with ctx.typing():
                response = await self.get_result(query)
                pages = []
                groups = [response[0][n : n + 3] for n in range(0, len(response[0]), 3)]
                for num, group in enumerate(groups, 1):
                    emb = discord.Embed(title=f"Google Search: {query[:50]}...")
                    for result in group:
                        emb.add_field(
                            name=f"{result.title}",
                            value=(f"[{result.url}]({result.url})\n" if result.url else "")
                            + f"{result.desc}"[:1024],
                            inline=False,
                        )
                    emb.description = f"Page {num} of {len(groups)}"
                    emb.set_footer(text=response[1])
                    pages.append(emb)
            if pages:
                await menus.menu(ctx, pages, controls=menus.DEFAULT_CONTROLS)
            else:
                await ctx.send("No result")

    @nsfwcheck()
    @google.command(alias="images")
    async def image(self, ctx, *, query: str = None):
        """Search google images from discord"""
        if not query:
            await ctx.send("Please enter some image name to search")
        else:
            async with ctx.typing():
                response = await self.get_result(query, images=True)
                size = len(tuple(response))
                pages = []
                for i, j in enumerate(response, 1):
                    pages.append(discord.Embed(title=f"Pages: {i}/{size}").set_image(url=j))
            if pages:
                await menus.menu(ctx, pages, controls=menus.DEFAULT_CONTROLS)
            else:
                await ctx.send("No result")

    def parser_text(self, text):
        """My bad logic for scraping"""
        soup = BeautifulSoup(text, features="html.parser")
        s = namedtuple("searchres", "url title desc")
        final = []
        stats = html2text.html2text(str(soup.find("div", id="result-stats")))
        if card := soup.find("div", class_="g mnr-c g-blk"):
            if desc := card.find("span", class_="hgKElc"):
                final.append(s(None, "Google Info Card:", html2text.html2text(str(desc))))
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

    def parser_image(self, html):
        soup = BeautifulSoup(html, features="html.parser")
        return [x.get("src", "https://http.cat/404") for x in soup.findAll("img", class_="t0fcAb")]

    async def get_result(self, query, images=False):
        """Fetch the data"""
        # TODO make this fetching a little better
        encoded = urllib.parse.quote_plus(query, encoding="utf-8", errors="replace")
        options = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        }
        if not images:
            url = "https://www.google.com/search?q="
            async with aiohttp.ClientSession() as session:
                async with session.get(url + encoded, headers=options) as resp:
                    text = await resp.text()
            prep = functools.partial(self.parser_text, text)
        else:
            # TYSM fixator, for the non-js query url
            url = "https://www.google.com/search?tbm=isch&sfr=gws&gbv=1&q="
            async with aiohttp.ClientSession() as session:
                async with session.get(url + encoded, headers=options) as resp:
                    text = await resp.text()
            prep = functools.partial(self.parser_image, text)
        return await self.bot.loop.run_in_executor(None, prep)
