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


def levenshtein_match_calc(s, t):
    """Copy pasta accuracy checker"""
    rows = len(s) + 1
    cols = len(t) + 1
    distance = [[0 for i in range(cols)] for j in range(rows)]

    for i in range(1, rows):
        for k in range(1, cols):
            distance[i][0] = i
            distance[0][k] = k

    for col in range(1, cols):
        for row in range(1, rows):
            if s[row - 1] == t[col - 1]:
                cost = 0
            else:
                cost = 2
            distance[row][col] = min(
                distance[row - 1][col] + 1,  # Cost of deletions
                distance[row][col - 1] + 1,  # Cost of insertions
                distance[row - 1][col - 1] + cost,
            )  # Cost of substitutions
    Ratio = ((len(s) + len(t)) - distance[row][col]) / (len(s) + len(t))
    return int(Ratio)


class TypeRacer(commands.Cog):
    """A Typing Speed test cog, to give test your typing skills"""

    def __init__(self, bot):
        self.bot = bot
        # self.config = Config.get_conf(self, identifier=109171231123)
        self.filter = HTMLFilter()
        # self.exclude = {'+', '|', '^', '`', '"', '$', ',', '!', '~', ':', '<', '#', '*', '-', '&', '(', '>', '%', ';', '}', "'", '_', '{', '=', ')', '?', '[', '/', '\\', ']', '.', '@'}

    @commands.group()
    async def typer(self, ctx):
        """Commands to start and stop personal typing speed test"""

    @typer.command(name="start")
    @commands.max_concurrency(1, commands.BucketType.user)
    async def start_personal(self, ctx):
        """Start a personal typing speed test"""
        self.player_id = ctx.author.id
        # Starting test after getting the text
        a_string = await self.get_text(ctx)
        self.task = asyncio.create_task(self.task_personal_race(ctx, a_string))
        temp = await self.task
        if temp:
            time_taken, b_string = temp
        else:
            return
        result = await self.evaluate(ctx, a_string, b_string, time_taken, True)

    async def task_personal_race(self, ctx, a_string):
        """Personal Race"""
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
            await msg.edit(content=f"{ctx.author.display_name} aborted the Typing test")
            return
        end = time.time()
        time_taken = end - start
        return time_taken, b_string

    @typer.command()
    async def stop(self, ctx):
        if hasattr(self, "task") and ctx.author.id == self.player_id:
            self.task.cancel()
        else:
            await ctx.send("You need to start the test.")

    @commands.group()
    async def typerset(self, ctx):
        """Settings for the typing speed test TODO"""

    @commands.group()
    @commands.mod_or_permissions(kick_members=True)
    async def speedevent(self, ctx):
        """Play a speed test event with multiple players"""

    @speedevent.command(name="start")
    async def start_event(self, ctx):
        """Start a typing speed test event \n(Be warned that cheating gets you disqualified)"""
        self.active = [ctx.author]
        a_string = await self.get_text(ctx)
        self.event = asyncio.create_task(self.task_event_race(ctx, a_string))
        await self.event

    @speedevent.command()
    async def join(self, ctx):
        if hasattr(self, "active"):
            self.active.append(ctx.author)
        elif hasattr(self, "event") and self.started == True:
            await ctx.author.send("Event already started")
        else:
            await ctx.send("No active events")

    async def task_event_race(self, ctx, a_string):
        """Event Race"""

        def evaluate_person_completion(message):
            if message.author in self.active:
                pass

        active = "\n".join(
            [
                f"{index}. {user.display_name}"
                for index, user in enumerate(self.active, 1)
            ]
        )
        countdown = await ctx.send(
            f"A Typing speed test event will commence in 60 seconds\n"
            f" Type `{ctx.prefix}speedevent join` to enter the race\n "
            f"Joined Users:\n{active}"
        )
        await asyncio.sleep(5)
        for i in range(55, 0, -5):
            active = "\n".join(
                [
                    f"{index}. {user.display_name}"
                    for index, user in enumerate(self.active, 1)
                ]
            )
            await countdown.edit(
                content=f"A Typing speed test event will commence in {i} seconds\n"
                f" Type `{ctx.prefix}speedevent join` to enter the race\n "
                f"Joined Users:\n{active}"
            )
            await asyncio.sleep(5)
        await countdown.edit(content=f"```{nocheats(a_string)}```")
        try:
            await self.bot.wait_for(
                "message",
                timeout=300.0,
                check=evaluate_person_completion,
            )
        except asyncio.TimeoutError:
            pass

    # Helper Functions
    async def evaluate(
        self, ctx, a_string: str, b_string: str, time_taken, personal: bool = False
    ):
        special_send = ctx.send if personal else ctx.author.send
        # TODO
        if "​" in b_string:
            if personal:
                await special_send(
                    "Imagine cheating bruh, c'mon atleast be honest here."
                )
            else:
                await special_send("You cheated and hence you are disqualified.")
            return
        else:
            mistakes = 0
            for i, s in enumerate(difflib.ndiff(a_string, b_string)):
                if s[0] == " ":
                    continue
                elif s[0] == "-" or s[0] == "+":
                    mistakes += 1
        # Analysis
        accuracy = levenshtein_match_calc(a_string, b_string)
        wpm = (len(a_string.split()) / time_taken) * 100
        if accuracy > 50:
            verdict = [
                ("WPM (Correct Words per minute)", wpm * accuracy),
                ("Raw WPM (Without accounting mistakes)", wpm),
                ("Accuracy", accuracy),
                ("Words Given", len(a_string.split())),
                (f"Words from {ctx.author.display_name}", len(b_string.split())),
                ("Characters Given", len(a_string)),
                (f"Characters from {ctx.author.display_name}", len(b_string)),
                (f"Mistakes done by {ctx.author.display_name}", mistakes),
            ]
            await special_send(content="```" + tabulate(verdict) + "```")
        else:
            await special_send(
                f"{ctx.author.display_name if personal else 'You'}  didn't want to complete the challenge."
            )

    async def get_text(self, ctx) -> str:
        """Gets the paragraph for the test"""
        # TODO add customisable length of text and difficuilty
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
            self.filter.feed(resp["text_out"])
            a_string = self.filter.text.strip()
            self.filter.text = ""
        return a_string

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
