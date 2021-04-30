import asyncio
import datetime
import functools
import json
import re
import textwrap
import urllib
from collections import namedtuple
from io import BytesIO

import aiohttp
import discord
from bs4 import BeautifulSoup
from html2text import html2text as h2t
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.vendored.discord.ext import menus

# TODO Add optional way to use from google search api


nsfwcheck = lambda ctx: (not ctx.guild) or ctx.channel.is_nsfw()


class Google(commands.Cog):
    """
    A Simple google search with image support as well
    A fair bit of querying stuff is taken from  Kowlin's cog - https://github.com/Kowlin/refactored-cogs
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.options = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        }
        self.link_regex = re.compile(
            r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*(?:\.png|\.jpe?g|\.gif))"
        )
        self.cookies = None

    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def google(self, ctx, *, query: str = None):
        """Search in google from discord"""
        if not query:
            await ctx.send("Please enter something to search")
        else:
            isnsfw = nsfwcheck(ctx)
            async with ctx.typing():
                response, kwargs = await self.get_result(query, nsfw=isnsfw)
                pages = []
                groups = [response[n : n + 3] for n in range(0, len(response), 3)]
                for num, group in enumerate(groups, 1):
                    emb = discord.Embed(
                        title="Google Search: {}".format(
                            query[:44] + "\N{HORIZONTAL ELLIPSIS}" if len(query) > 45 else query
                        ),
                        color=await ctx.embed_color(),
                    )
                    for result in group:
                        desc = (
                            f"[{result.url[:60]}]({result.url})\n" if result.url else ""
                        ) + f"{result.desc}"[:1024]
                        emb.add_field(
                            name=f"{result.title}",
                            value=desc or "Nothing",
                            inline=False,
                        )
                    emb.description = f"Page {num} of {len(groups)}"
                    emb.set_footer(
                        text=f"Safe Search: {not isnsfw} | " + kwargs["stats"].replace("\n", " ")
                    )
                    if "thumbnail" in kwargs:
                        emb.set_thumbnail(url=kwargs["thumbnail"])

                    if "image" in kwargs and num == 1:
                        emb.set_image(url=kwargs["image"])
                    pages.append(emb)
            if pages:
                await ResultMenu(source=Source(pages, per_page=1)).start(ctx)
            else:
                await ctx.send("No result")

    @google.command()
    async def autofill(self, ctx, *, query: str):
        """Responds with a list of the Google Autofill results for a particular query."""

        # This “API” is a bit of a hack; it was only meant for use by
        # Google’s own products. and hence it is undocumented.
        # Attribution: https://shreyaschand.com/blog/2013/01/03/google-autocomplete-api/
        base_url = "https://suggestqueries.google.com/complete/search"
        params = {"client": "firefox", "hl": "en", "q": query}
        async with ctx.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(base_url, params=params) as response:
                        if response.status != 200:
                            return await ctx.send(f"https://http.cat/{response.status}")
                        data = json.loads(await response.read())
            except asyncio.TimeoutError:
                return await ctx.send("Operation timed out.")

            if not data[1]:
                return await ctx.send("Could not find any results.")

            await ctx.send("\n".join(data[1]))

    @google.command()
    async def doodle(self, ctx, month: int = None, year: int = None):
        """Responds with today's Google doodle."""
        month = datetime.datetime.now(datetime.timezone.utc).month if not month else month
        year = datetime.datetime.now(datetime.timezone.utc).year if not year else year

        async with ctx.typing():
            base_url = f"https://www.google.com/doodles/json/{year}/{month}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(base_url) as response:
                        if response.status != 200:
                            return await ctx.send(f"https://http.cat/{response.status}")
                        output = await response.json()
            except asyncio.TimeoutError:
                return await ctx.send("Operation timed out.")

            if not output:
                return await ctx.send("Could not find any results.")

            pages = []
            for data in output:
                em = discord.Embed(colour=await ctx.embed_color())
                em.title = data.get("title", "Doodle title missing")
                img_url = data.get("high_res_url")
                if (img_url and not img_url.startswith("https:")):
                    img_url = "https:" + data.get("high_res_url")
                if not img_url:
                    img_url = "https:" + data.get("url")
                em.set_image(url=img_url)
                date = "-".join([str(x) for x in data.get("run_date_array")[::-1]])
                em.set_footer(text=f"{data.get('share_text')}\nDoodle published on: {date}")
                pages.append(em)

        if len(pages) == 1:
            return await ctx.send(embed=pages[0])
        else:
            await ResultMenu(source=Source(pages, per_page=1)).start(ctx)

    @google.command(aliases=["img"])
    async def image(self, ctx, *, query: str = None):
        """Search google images from discord"""
        if not query:
            await ctx.send("Please enter some image name to search")
        else:
            isnsfw = nsfwcheck(ctx)
            async with ctx.typing():
                response = await self.get_result(query, images=True, nsfw=isnsfw)
                size = len(tuple(response))
                pages = [
                    discord.Embed(
                        title=f"Pages: {i}/{size}",
                        color=await ctx.embed_color(),
                        description="Some images might not be visible.",
                    )
                    .set_image(url=j)
                    .set_footer(text=f"Safe Search: {not isnsfw}")
                    for i, j in enumerate(response, 1)
                ]

            if pages:
                await ResultMenu(source=Source(pages, per_page=1)).start(ctx)
            else:
                await ctx.send("No result")

    @google.command(aliases=["rev"])
    async def reverse(self, ctx, *, url: str = None):
        """Attach or paste the url of an image to reverse search, or reply to a message which has the image/embed with the image"""
        isnsfw = nsfwcheck(ctx)
        query = None

        def reply(ctx):
            # Helper reply grabber
            if hasattr(ctx.message, "reference") and ctx.message.reference != None:
                msg = ctx.message.reference.resolved
                if isinstance(msg, discord.Message):
                    return msg

        def get_url(msg_obj, check=False):
            # Helper get potential url, if check is True then returns none if nothing is found in embeds
            if msg_obj.embeds:
                emb = msg_obj.embeds[0].to_dict()
                if "image" in emb:
                    return emb["image"]["url"]
                elif "thumbnail" in emb:
                    return emb["thumbnail"]["url"]
            if msg_obj.attachments:
                return msg_obj.attachments[0].url
            else:
                return None if check else msg_obj.content.lstrip("<").rstrip(">")

        def check_url(url: str):
            # Helper function to check if valid url or not
            return url.startswith("http") and " " not in url

        if resp := reply(ctx):
            query = get_url(resp)

        # TODO More work on this to shorten code.
        if not query or not check_url(query):
            if query := get_url(ctx.message, check=True):
                pass
            elif url is None:
                return await ctx.send_help()
            else:
                query = url.lstrip("<").rstrip(">")

        # Big brain url parsing
        if not check_url(query):
            return await ctx.send_help()

        if not query or not query.startswith("http") or " " in query:
            return await ctx.send_help()

        encoded = {
            "image_url": query,
            "encoded_image": None,
            "image_content": None,
            "filename": None,
            "hl": "en",
        }

        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.google.com/searchbyimage?" + urllib.parse.urlencode(encoded),
                    headers=self.options,
                    cookies=self.cookies,
                ) as resp:
                    text = await resp.read()
                    redir_url = resp.url
            prep = functools.partial(self.reverse_search, text)
            result, (response, kwargs) = await self.bot.loop.run_in_executor(None, prep)
            pages = []
            if response:
                groups = [response[n : n + 3] for n in range(0, len(response), 3)]
                for num, group in enumerate(groups, 1):
                    emb = discord.Embed(
                        title="Google Reverse Image Search",
                        description="[`"
                        + (result or "Nothing significant found")
                        + f"`]({redir_url})",
                        color=await ctx.embed_color(),
                    )
                    for i in group:
                        desc = (f"[{i.url[:60]}]({i.url})\n" if i.url else "") + f"{i.desc}"[:1024]
                        emb.add_field(
                            name=f"{i.title}",
                            value=desc or "Nothing",
                            inline=False,
                        )
                    emb.set_footer(
                        text=f"Safe Search: {not isnsfw} | "
                        + kwargs["stats"].replace("\n", " ")
                        + f"| Page: {num}/{len(groups)}"
                    )
                    emb.set_thumbnail(url=encoded["image_url"])
                    pages.append(emb)
            if pages:
                await ResultMenu(source=Source(pages, per_page=1)).start(ctx)
            else:
                await ctx.send(
                    embed=discord.Embed(
                        title="Google Reverse Image Search",
                        description="[`" + ("Nothing significant found") + f"`]({redir_url})",
                        color=await ctx.embed_color(),
                    ).set_thumbnail(url=encoded["image_url"])
                )

    @commands.is_owner()
    @google.command(hidden=True)
    async def debug(self, ctx, *, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.options, cookies=self.cookies) as resp:
                text = await resp.text()
        f = BytesIO(bytes(text, "utf-8"))
        await ctx.send(file=discord.File(f, filename="filename.html"))
        f.close()

    async def get_result(self, query, images=False, nsfw=False):
        """Fetch the data"""
        # TODO make this fetching a little better
        encoded = urllib.parse.quote_plus(query, encoding="utf-8", errors="replace")

        async def get_html(url, encoded):
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url + encoded, headers=self.options, cookies=self.cookies
                ) as resp:
                    self.cookies = resp.cookies
                    return await resp.text()

        if not nsfw:
            encoded += "&safe=active"
        if not images:
            url = "https://www.google.com/search?q="
            text = await get_html(url, encoded)
            prep = functools.partial(self.parser_text, text)
        else:
            # TYSM fixator, for the non-js query url
            url = "https://www.google.com/search?tbm=isch&q="
            text = await get_html(url, encoded)
            prep = functools.partial(self.parser_image, text)
        return await self.bot.loop.run_in_executor(None, prep)

    def reverse_search(self, text):
        soup = BeautifulSoup(text, features="html.parser")
        if check := soup.find("div", class_="card-section"):
            if "The URL doesn't refer" in check.text:
                return check.text, (None, None)
        if res := soup.find("input", class_="gLFyf gsfi"):
            return res["value"], self.parser_text(text, soup=soup, cards=False)

    def parser_text(self, text, soup=None, cards: bool = True):
        """My bad logic for scraping"""
        if not soup:
            soup = BeautifulSoup(text, features="html.parser")
        s = namedtuple("searchres", "url title desc")
        final = []
        kwargs = {"stats": h2t(str(soup.find("div", id="result-stats")))}

        def get_card():
            """Getting cards if present, here started the pain"""
            # common card
            if card := soup.find("div", class_="g mnr-c g-blk"):
                if desc := card.find("span", class_="hgKElc"):
                    final.append(s(None, "Google Info Card:", h2t(str(desc))))
                    return

            # calculator card
            if card := soup.find("div", class_="tyYmIf"):
                if question := card.find("span", class_="vUGUtc"):
                    if answer := card.find("span", class_="qv3Wpe"):
                        tmp = h2t(str(question)).strip("\n")
                        final.append(
                            s(None, "Google Calculator:", f"**{tmp}** {h2t(str(answer))}")
                        )
                        return

            # sidepage card
            if card := soup.find("div", class_="liYKde g VjDLd"):
                if thumbnail := card.find("g-img", attrs={"data-lpage": True}):
                    kwargs["thumbnail"] = thumbnail["data-lpage"]
                if title := soup.find("div", class_="SPZz6b"):
                    if desc := card.find("div", class_="kno-rdesc"):
                        if remove := desc.find(class_="Uo8X3b"):
                            remove.decompose()

                        desc = (
                            textwrap.shorten(
                                h2t(str(desc)), 1024, placeholder="\N{HORIZONTAL ELLIPSIS}"
                            )
                            + "\n"
                        )

                        if more_info := card.findAll("div", class_="Z1hOCe"):
                            for thing in more_info:
                                tmp = thing.findAll("span")
                                if len(tmp) == 2:
                                    desc2 = f"\n **{tmp[0].text}**`{tmp[1].text.lstrip(':')}`"
                                    # More jack advises :D
                                    MAX = 1024
                                    MAX_LEN = MAX - len(desc2)
                                    if len(desc) > MAX_LEN:
                                        desc = (
                                            next(
                                                pagify(
                                                    desc,
                                                    delims=[" ", "\n"],
                                                    page_length=MAX_LEN - 1,
                                                    shorten_by=0,
                                                )
                                            )
                                            + "\N{HORIZONTAL ELLIPSIS}"
                                        )
                                    desc = desc + desc2
                        final.append(
                            s(
                                None,
                                "Google Featured Card: "
                                + h2t(str(title)).replace("\n", " ").replace("#", ""),
                                desc,
                            )
                        )
                    return

            # time cards and unit conversions and moar-_- WORK ON THIS, THIS IS BAD STUFF 100
            if card := soup.find("div", class_="vk_c"):
                if conversion := card.findAll("div", class_="rpnBye"):
                    if len(conversion) != 2:
                        return
                    tmp = tuple(
                        map(
                            lambda thing: (
                                thing.input["value"],
                                thing.findAll("option", selected=True)[0].text,
                            ),
                            conversion,
                        )
                    )
                    final.append(
                        s(
                            None,
                            "Unit Conversion v1:",
                            "`" + " ".join(tmp[0]) + " is equal to " + " ".join(tmp[1]) + "`",
                        )
                    )
                    return
                elif card.find("div", "lu_map_section"):
                    if img := re.search(r"\((.*)\)", h2t(str(card)).replace("\n", "")):
                        kwargs["image"] = "https://www.google.com" + img[1]
                        return
                else:
                    # time card
                    if tail := card.find("table", class_="d8WIHd"):
                        tail.decompose()
                    tmp = h2t(str(card)).replace("\n\n", "\n").split("\n")
                    final.append(s(None, tmp[0], "\n".join(tmp[1:])))
                    return

            # translator cards
            if card := soup.find("div", class_="tw-src-ltr"):
                langs = soup.find("div", class_="pcCUmf")
                src_lang = "**" + langs.find("span", class_="source-language").text + "**"
                dest_lang = "**" + langs.find("span", class_="target-language").text + "**"
                final_text = ""
                if source := card.find("div", id="KnM9nf"):
                    final_text += (src_lang + "\n`" + source.find("pre").text) + "`\n"
                if dest := card.find("div", id="kAz1tf"):
                    final_text += dest_lang + "\n`" + dest.find("pre").text.strip("\n") + "`"
                final.append(s(None, "Google Translator", final_text))
                return

            # Unit conversions
            if card := soup.find("div", class_="nRbRnb"):
                final_text = "\N{ZWSP}\n**"
                if source := card.find("div", class_="vk_sh c8Zgcf"):
                    final_text += "`" + h2t(str(source)).strip("\n")
                if dest := card.find("div", class_="dDoNo ikb4Bb vk_bk gsrt gzfeS"):
                    final_text += " " + h2t(str(dest)).strip("\n") + "`**"
                if time := card.find("div", class_="hqAUc"):
                    if remove := time.find("select"):
                        remove.decompose()
                    tmp = h2t(str(time)).replace("\n", " ").split("·")
                    final_text += (
                        "\n"
                        + (f"`{tmp[0].strip()}` ·{tmp[1]}" if len(tmp) == 2 else "·".join(tmp))
                        + "\n\N{ZWSP}"
                    )
                final.append(s(None, "Unit Conversion", final_text))
                return

            # Definition cards
            if card := soup.find("div", class_="KIy09e"):
                final_text = ""
                if word := card.find("div", class_="DgZBFd XcVN5d frCXef"):
                    if sup := word.find("sup"):
                        sup.decompose()
                    final_text += "`" + word.text + "`"
                if pronounciate := card.find("div", class_="S23sjd g30o5d"):
                    final_text += "   |   " + pronounciate.text
                if type_ := card.find("div", class_="pgRvse vdBwhd ePtbIe"):
                    final_text += "   |   " + type_.text + "\n\n"
                if definition := card.find("div", class_="L1jWkf h3TRxf"):
                    for text in definition.findAll("div")[:2]:
                        tmp = h2t(str(text))
                        if tmp.count("\n") < 5:
                            final_text += "`" + tmp.strip("\n").replace("\n", " ") + "`" + "\n"
                final.append(s(None, "Definition", final_text))
                return

            # single answer card
            if card := soup.find("div", class_="ayRjaf"):
                final.append(
                    s(
                        None,
                        h2t(str(card.find("div", class_="zCubwf"))).replace("\n", ""),
                        h2t(str(card.find("span").find("span"))).strip("\n") + "\n\N{ZWSP}",
                    )
                )
                return
            # another single card?
            if card := soup.find("div", class_="sXLaOe"):
                final.append(s(None, "Single Answer Card:", card.text))
                return

        if cards:
            get_card()
        for res in soup.findAll("div", class_="g"):
            if name := res.find("div", class_="yuRUbf"):
                url = name.a["href"]
                if title := name.find("h3", "LC20lb DKV0Md"):
                    title = title.text
                else:
                    title = url
            else:
                url = None
                title = None
            if desc := res.find("div", class_="IsZvec"):
                if remove := desc.find("span", class_="f"):
                    remove.decompose()
                desc = h2t(str(desc.find("span", class_="aCOpRe")))
            else:
                desc = "Not found"
            if title:
                final.append(s(url, title, desc.replace("\n", " ")))
        return final, kwargs

    def parser_image(self, html):
        # first 2 are google static logo images
        return self.link_regex.findall(html)[2:]


# Dpy menus
class Source(menus.ListPageSource):
    async def format_page(self, menu, embeds):
        return embeds


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
