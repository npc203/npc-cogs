from redbot.core import commands, data_manager, checks, Config
import asyncio, aiohttp
from html.parser import HTMLParser
import random, time, difflib
from tabulate import tabulate


class HTMLFilter(HTMLParser):
    """For HTML to text properly without any dependencies.
    Credits: https://gist.github.com/ye/050e898fbacdede5a6155da5b3db078d"""

    text = ""

    def handle_data(self, data):
        self.text += data


def nocheats(text: str) -> str:
    """To catch Cheaters upto some extent"""
    text = list(text)
    size = len(text)
    for _ in range(size // 5):
        text.insert(random.randint(0, size), "​")
    return "".join(text)


class TypeRacer(commands.Cog):
    """A Typing Speed test cog, to give test your typing skills"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=109171231123)
        self.filter = HTMLFilter()
        # self.exclude = {'+', '|', '^', '`', '"', '$', ',', '!', '~', ':', '<', '#', '*', '-', '&', '(', '>', '%', ';', '}', "'", '_', '{', '=', ')', '?', '[', '/', '\\', ']', '.', '@'}

    async def task_race(self, ctx, a_string):
        """the race starts and ends here"""
        msg = await ctx.send(
            f"{ctx.author.display_name} started a typing test: \n Let's Start in 3"
        )
        for i in range(2, 0, -1):
            await asyncio.sleep(1)
            await msg.edit(
                content=f"{ctx.author.display_name} started a typing test: \n Let's Start in {i}"
            )
        await asyncio.sleep(1)
        await msg.edit(content="```" + nocheats(a_string) + "```")
        start = time.time()
        try:
            b_string = (
                await self.bot.wait_for(
                    "message",
                    timeout=300.0,
                    check=lambda m: m.author.id == ctx.author.id,
                )
            ).content.strip()
        except asyncio.TimeoutError:
            await msg.edit(content="Sorry you were way too slow, timed out")
            return
        except asyncio.CancelledError:
            await msg.edit(content="The User aborted the Typing test")
            return
        end = time.time()
        time_taken = end - start
        return time_taken, b_string

    @commands.group()
    async def typer(self, ctx):
        """Commands to start and stop the typing speed test"""

    @typer.command()
    @commands.max_concurrency(1, commands.BucketType.user)
    async def start(self, ctx):
        """Start the typing speed test"""
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://www.randomtext.me/api/gibberish/p-1/25-45"
                ) as f:
                    if f.status == 200:
                        resp = await f.json()
                    else:
                        await ctx.send(f"Something went wrong, ERROR CODE:{f.status}")
                        return
        data = resp["text_out"]
        self.player_id = ctx.author.id

        # Starting test after getting the text
        self.filter.feed(data)
        a_string = self.filter.text.strip()
        self.filter.text = ""

        self.task = asyncio.create_task(self.task_race(ctx, a_string))
        temp = await self.task
        if temp:
            time_taken, b_string = temp
        else:
            return

        # Post test calculations
        if "​" in b_string:
            await ctx.send("Imagine cheating bruh, c'mon atleast be honest here.")
            return
        else:
            mistakes = 0
            for i, s in enumerate(difflib.ndiff(a_string, b_string)):
                if s[0] == " ":
                    continue
                elif s[0] == "-" or s[0] == "+":
                    mistakes += 1
        # Analysis
        wpm = ((len(a_string.split()) - mistakes) / time_taken) * 100
        player_id = ctx.author.id
        if wpm > 0:
            verdict = [
                ("WPM (Correct Words per minute)", wpm),
                ("Words Given", len(a_string.split())),
                (f"Words from {ctx.author.display_name}", len(b_string.split())),
                ("Characters Given", len(a_string)),
                (f"Characters from {ctx.author.display_name}", len(b_string)),
                (f"Mistakes done by {ctx.author.display_name}", mistakes),
            ]
            note = "Every mistaken characters accounts for a mistaken word.\nExample: If a word contains 2 mistaken characters then 2 words are considered wrong"
            await ctx.send(content="```" + tabulate(verdict) + "```\nNote:\n" + note)
        else:
            await ctx.send(
                f"{ctx.author.display_name} didn't want to complete the challenge."
            )

    @typer.command()
    async def stop(self, ctx):
        if hasattr(self, "task") and ctx.author.id == self.player_id:
            self.task.cancel()
        else:
            await ctx.send("You need to start the test.")

    @commands.group()
    async def typerset(self, ctx):
        """Settings for the typing speed test"""

    async def on_command_error(self, ctx, error):
        await ctx.message.delete()
        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.author.send("Only One Test per person")
        else:
            await self.bot.on_command_error(ctx, error, unhandled_by_cog=True)

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
