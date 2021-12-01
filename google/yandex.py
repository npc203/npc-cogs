import functools
import json
import urllib

import discord
from bs4 import BeautifulSoup
from redbot.core import commands

from .utils import get_query


class Yandex:
    @commands.group()
    async def yandex(self, ctx):
        """Yandex related search commands"""

    @yandex.command(name="reverse", aliases=["rev"])
    async def yandex_reverse(self, ctx, *, url: str = None):
        """Attach or paste the url of an image to reverse search, or reply to a message which has the image/embed with the image"""

        if query := get_query(ctx, url):
            pass
        else:
            return await ctx.send_help()

        encoded = {
            "rpt": "imageview",
            "url": query,
            "format": "json",
            "request": {
                "blocks": [
                    {"block": "extra-content", "params": {}, "version": 2},
                    {"block": "i-global__params:ajax", "params": {}, "version": 2},
                    {"block": "suggest2-history", "params": {}, "version": 2},
                    {"block": "cbir-intent__image-link", "params": {}, "version": 2},
                    {"block": "content_type_search-by-image", "params": {}, "version": 2},
                    {"block": "serp-controller", "params": {}, "version": 2},
                    {"block": "cookies_ajax", "params": {}, "version": 2},
                    {"block": "advanced-search-block", "params": {}, "version": 2},
                ],
                "metadata": {
                    "bundles": {"lb": "n?O/G?b*G$"},
                    "assets": {
                        "las": "justifier-height=1;thumb-underlay=1;justifier-setheight=1;fitimages-height=1;justifier-fitincuts=1;react-with-dom=1;720.0=1;616.0=1;6022a8.0=1;0e3c2c.0=1;464.0=1;da4144.0=1"
                    },
                    "version": "0x32f8444edac",
                    "extraContent": {"names": ["i-react-ajax-adapter"]},
                },
            },
        }

        async with ctx.typing():
            async with self.session.get(
                "https://yandex.com/images/search?" + urllib.parse.urlencode(encoded),
                headers=self.options,
            ) as resp:
                text = await resp.read()
                await ctx.send(text)
                redir_url = resp.url
            prep = functools.partial(self.yandex_reverse_search, text)
            result = await self.bot.loop.run_in_executor(None, prep)
            if result:
                result = json.loads(result)["tags"]
                emb = discord.Embed(
                    title="Yandex Reverse Image Search",
                    description=f"[`Cliek here to View in Browser`]({redir_url})\n",
                    color=await ctx.embed_color(),
                )
                emb.add_field(
                    name="Results",
                    value="\n".join(
                        map(lambda x: f"[{x['text']}]({'https://yandex.com'+x['url']})", result)
                    ),
                )
                emb.set_footer(text="Powered by yandex")
                emb.set_thumbnail(url=query)
                await ctx.send(embed=emb)
            else:
                await ctx.send(
                    embed=discord.Embed(
                        title="Yandex Reverse Image Search",
                        description="[`" + ("Nothing relevant found") + f"`]({redir_url})",
                        color=await ctx.embed_color(),
                    ).set_thumbnail(url=query)
                )

    def yandex_reverse_search(self, text):
        soup = BeautifulSoup(text, features="html.parser")
        if sidebar := soup.find(
            "div",
            class_="cbir-search-by-image-page__section cbir-search-by-image-page__section_name_tags",
        ):
            if check := sidebar.find("div", {"data-state": True}):
                return check["data-state"]
