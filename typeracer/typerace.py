from redbot.core import commands, data_manager,checks
import asyncio
from html.parser import HTMLParser
import random,time,difflib
from tabulate import tabulate
from essential_generators import DocumentGenerator

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

class TypeRacer(commands.Cog):
    """A Typing Speed test cog, to give test your typing skills"""
    def __init__(self, bot):
        self.bot = bot
        self.filter = HTMLFilter()
        self.exclude = {'+', '|', '^', '`', '"', '$', ',', '!', '~', ':', '<', '#', '*', '-', '&', '(', '>', '%', ';', '}', "'", '_', '{', '=', ')', '?', '[', '/', '\\', ']', '.', '@'}

    @commands.command()
    async def racestart(self,ctx):
        async with ctx.typing():
            gen = DocumentGenerator()
            data = ''.join(ch for ch in gen.paragraph() if ch not in self.exclude)
            data = "".join(filter(lambda x : (x.isalpha or x == " "), data))
            data = data.split()
            data = ' '.join(data[0:random.randint(25,45)])
        #Starting test after getting the text
        self.filter.feed(data)
        a_string = self.filter.text
        self.filter.text = ""
        msg = await ctx.send(f"{ctx.author.display_name} started a typing test: \n Let's Start in 3")
        for i in range(2,0,-1):
            await asyncio.sleep(1)
            await msg.edit(content=f"{ctx.author.display_name} started a typing test: \n Let's Start in {i}")  
        await asyncio.sleep(1)   
        await msg.edit(content="```"+nocheats(a_string)+"```")
        start = time.time()
        try:
            self.task = asyncio.create_task(self.bot.wait_for('message',timeout=300.0,check = lambda m: m.author.id == ctx.author.id ))
            b_string = (await self.task).content.strip()
        except asyncio.TimeoutError:
            await msg.edit(content="Sorry you were way too slow, timed out")
            return  
        except asyncio.CancelledError:
            await msg.edit(content="The User aborted the Typing test")
            return
        end = time.time()

        #Post test calculations
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
        #Analysis
        wpm = ((len(a_string.split())-mistakes)/time_taken)*100
        author = ctx.author.display_name
        verdict = [
                    ("WPM (Correct Words per minute)",wpm),
                    ("Words Given",len(a_string.split())),
                    (f"Words from {author}",len(b_string.split())),
                    ("Characters Given",len(a_string)),
                    (f"Characters from {author}",len(b_string)),
                    (f"Mistakes done by {author}",mistakes),
                ]
        note = "Every mistaken characters accounts for a mistaken word.\n example: If a word contains 2 mistaken characters then 2 words are considered wrong"
        await ctx.send(content = '```'+tabulate(verdict)+'```\nNote:\n'+note)
        

    @commands.command()
    async def racestop(self,ctx):
        if 'task' in dir(self):
            self.task.cancel()
        else:
            await ctx.send("You need to start the test.")
        
    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass

