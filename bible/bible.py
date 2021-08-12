import discord
import aiohttp
from bs4 import BeautifulSoup
from html2text import html2text as h2t
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS


class Bible(commands.Cog):
    """
    Pull up biblical verses fast
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

    @commands.command()
    async def bible(self, ctx, *, args):
        """
        Pull up bible verses
        """
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.biblegateway.com/passage/?search=" + args) as resp:
                    soup = BeautifulSoup(await resp.text(), "html.parser")
                    text = soup.find("div", {"class": "std-text"})
                    # Remove cross references
                    for sup in text.find_all("sup", {"class": "crossreference"}):
                        sup.decompose()

                    # Change headers to markdown
                    for h3 in text.find_all("h3"):
                        h3.name = "b"
                    for h4 in text.find_all("h4"):
                        h4.name = "b"

                    text = h2t(str(text))
                
                full_chap = None
                if full_chap := soup.find("a",{"class":"full-chap-link"}):
                    full_chap = "https://www.biblegateway.com"+full_chap.get("href") 
                   
                title = soup.find("div",{"class":"dropdown-display-text"}).text
                pages = []
                raw = list(pagify(text ,page_length=4000))
                size = len(raw)
                emb_color = await ctx.embed_color()
                for i,page in enumerate(raw,1):
                    emb = discord.Embed(title=title, description=page, colour=emb_color)
                    emb.url = full_chap         
                    emb.set_footer(text=f"Powered by Biblegateway.com | Page {i}/{size}")
                    pages.append(emb)
        await menu(ctx, pages, DEFAULT_CONTROLS)

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        return
