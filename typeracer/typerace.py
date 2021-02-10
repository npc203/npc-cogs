import asyncio
import random
import time

from .single import Single
from .speedevent import Speedevent
from tabulate import tabulate
from redbot.core import Config, checks, commands, data_manager


class TypeRacer(commands.Cog):
    """A Typing Speed test cog, to give test your typing skills"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=29834829369)
        default_global = {
            "time_start": 60,
            "text_size": [25, 45],
            "type": "gibberish",
            "image": False,
        }
        default_guild = {
            "time_start": 60,
            "text_size": [25, 45],
            "type": "gibberish",
            "accuracy": 66,
            "image": False,
        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.jobs = {"guilds": {}, "personal": {}}

    @commands.group()
    async def typer(self, ctx):
        """Commands to start and stop personal typing speed test"""

    @typer.command(name="start")
    async def start_personal(self, ctx):
        """Start a personal typing speed test"""
        if ctx.author.id in self.jobs["personal"]:
            await ctx.send("You already are running a speedtest")
        else:
            test = Single(ctx)
            self.jobs["personal"][ctx.author.id] = test
            await test.start()
            self.jobs["personal"].pop(ctx.author.id)

    @typer.command()
    async def stop(self, ctx):
        if ctx.author.id in self.jobs["personal"]:
            await self.jobs["personal"][ctx.author.id].cancel()
        else:
            await ctx.send("You need to start the test.")

    @commands.guild_only()
    @commands.group()
    async def speedevent(self, ctx):
        """Play a speed test event with multiple players"""

    @commands.mod_or_permissions(kick_members=True)
    @speedevent.command(name="start")
    async def start_event(self, ctx):
        """Start a typing speed test event \n(Be warned that cheating gets you disqualified)"""
        if ctx.guild.id in self.jobs["guilds"]:
            await ctx.send("There's already a speedtest event running in this guild")
        else:
            test = Speedevent(ctx)
            self.jobs["guilds"][ctx.guild.id] = test
            await test.start()
            self.jobs["guilds"].pop(ctx.guild.id)

    @speedevent.command()
    async def join(self, ctx):
        """Join the typing test speed event"""
        if ctx.guild.id in self.jobs["guilds"]:
            await self.jobs["guilds"][ctx.guild.id].join(ctx.author.id,ctx.author.display_name)
        else:
            await ctx.send("Event has not started yet")

    @commands.group()
    async def typerset(self, ctx):
        """Settings for the typing speed test TODO"""

    @typerset.command()
    async def time(self, ctx, num: int):
        """Sets the time delay (in seconds) to start a speedtest event (max limit = 1000 seconds)"""
        if num <= 1000:
            await self.config.guild(ctx.guild).time_start.set(num)
            await ctx.send(f"Changed delay to {num}")
        else:
            await ctx.send("Max limit is 1000 seconds")

    @commands.is_owner()  # TODO
    @typerset.group(name="global")
    async def global_conf(self, ctx):
        """Global settings for the typeracer cog"""

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
