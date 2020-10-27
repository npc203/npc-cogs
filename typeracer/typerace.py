from redbot.core import commands, data_manager,checks
import aiohttp,asyncio
from html.parser import HTMLParser
import random,time,difflib

class HTMLFilter(HTMLParser):
    """For HTML to text properly without any dependencies.
    Credits: https://gist.github.com/ye/050e898fbacdede5a6155da5b3db078d"""
    text = ""
    def handle_data(self, data):
        self.text += data

def nocheats(text:str) -> str:
    """To catch Cheaters upto some extent (injects zwsp)"""
    text = list(text)
    size = len(text)
    for i in range(size//5):
        text.insert(random.randint(0,size),"​")
    return "".join(text)

class TypeRace(commands.Cog):
    """A Typing Speed test cog, to give test your typing skills"""
    def __init__(self, bot):
        self.bot = bot
        self.filter = HTMLFilter()

    @commands.command()
    async def racestart(self,ctx):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get("http://www.randomtext.me/api/gibberish/p-1/25-45") as f:
                    if f.status == 200:
                        resp=await f.json()
                    else:
                        await ctx.send(f"Something went wrong, ERROR CODE:{f.status}")
                        return
        a_string = self.filter.feed(resp["text_out"])
        msg = await ctx.send(f"{ctx.author.display_name} started a typing test: \n Let's Start in 3")
        for i in range(2,0,-1):
            asyncio.sleep(1)
            await msg.edit("Let's Start in {i}")     
        await msg.edit("`"+nocheats(a_string)+"`")
        start = time.time()
        b_string = await self.bot.wait_for('message',timeout=120.0,check = lambda m: m.author.id == ctx.author.id )
        end = time.time()
        if "​" in b_string:
            await ctx.send("Imagine cheating bruh, cm'on atleast be honest here.")
            return
        else:
            mistakes = 0
            time_taken = end - start
            for i,s in enumerate(difflib.ndiff(a_string, b_string)):
                if s[0]==' ': continue
                elif s[0]=='-' or s[0]=='+':
                    mistakes+=1
            wpm = ((len(a_string)-mistakes)/time_taken)*100
        

    @commands.command()
    async def racestop(self,ctx,*,cmd:str):
        pass

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass

