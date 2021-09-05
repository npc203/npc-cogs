from discord import Embed
from redbot.core import Config, commands

from .single import Single
from .speedevent import Speedevent
from .utils import typerset_check


class TypeRacer(commands.Cog):
    """A Typing Speed test cog, to give test your typing skills"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=29834829369)
        default_guild = {
            "time_start": 60,
            "text_size": (10, 20),
            "type": "gibberish",
            "dm": True,
        }
        self.config.register_guild(**default_guild)
        default_user = {
            "text_size": (10, 20),
            "type": "gibberish",
        }
        self.config.register_user(**default_user)

        self.jobs = {"guilds": {}, "personal": {}}

    @commands.group()
    async def typer(self, ctx):
        """Commands to start and stop personal typing speed test"""

    @typer.command()
    async def settings(self, ctx):
        """Shows the current setting in the guild"""
        emb = Embed(color=await ctx.embed_color())
        settings = (
            await self.config.guild_from_id(ctx.guild.id).all()
            if ctx.guild
            else await self.config.user_from_id(ctx.author.id).all()
        )

        val = (
            f"`Type       `:{settings['type']}\n"
            + (
                (f"`Send dms   `:{settings['dm']}\n" + f"`Start timer`:{settings['time_start']}\n")
                if ctx.guild
                else ""
            )
            + f"`No of Words`:{settings['text_size'][0]} - {settings['text_size'][1]}\n"
        )
        emb.add_field(name="TyperRacer settings", value=val)
        await ctx.send(embed=emb)

    @commands.is_owner()
    @typer.command()
    async def show(self, ctx):
        """Show the details of ongoing typer events globally"""
        emb = Embed(title="Ongoing Type racer stats", color=await ctx.embed_color())
        if self.jobs["guilds"]:
            emb.add_field(name="Speedevents", value=len(self.jobs["guilds"]))
        if self.jobs["personal"]:
            emb.add_field(name="Personal typing tests", value=len(self.jobs["personal"]))
        await ctx.send(embed=emb)

    @typer.command(name="start")
    async def start_personal(self, ctx):
        """Start a personal typing speed test"""
        if ctx.author.id in self.jobs["personal"]:
            await ctx.send("You already are running a speedtest")
        else:
            test = Single(
                ctx,
                await (
                    self.config.guild_from_id(ctx.guild.id).all()
                    if ctx.guild
                    else self.config.user_from_id(ctx.author.id).all()
                ),
            )
            self.jobs["personal"][ctx.author.id] = test
            await test.start()
            self.jobs["personal"].pop(ctx.author.id)

    @typer.command()
    async def stop(self, ctx):
        """Stop/Cancel taking the personal typing test"""
        if ctx.author.id in self.jobs["personal"]:
            await self.jobs["personal"][ctx.author.id].cancel()
        else:
            await ctx.send("You need to start the test.")

    @commands.guild_only()
    @commands.group()
    async def speedevent(self, ctx):
        """Play a speed test event with multiple players"""

    @commands.mod_or_permissions(manage_messages=True)
    @speedevent.command(name="start")
    async def start_event(self, ctx, countdown: int = None, *, args=""):
        """Start a typing speed test event
        Use `--all` for everyone to be added to the contest

        Takes an optional countdown argument to start the test
        (Be warned that cheating gets you disqualified)

        This lasts for 3 minutes at max, and stops if everyone completed

        Examples:
        `[p]speedevent start`
        `[p]speedevent start 20`
        `[p]speedevent start 30 --all`
        """
        if ctx.guild.id in self.jobs["guilds"]:
            await ctx.send("There's already a speedtest event running in this guild")
        elif countdown and countdown > 300:
            await ctx.send("Exceeded time limit for countdown, Enter value less than 300 seconds")
        else:
            test = Speedevent(
                ctx,
                countdown or await self.config.guild_from_id(ctx.guild.id).time_start(),
                await self.config.guild_from_id(ctx.guild.id).all(),
                all=True if "--all" in args else False,
            )
            self.jobs["guilds"][ctx.guild.id] = test
            await test.start()
            self.jobs["guilds"].pop(ctx.guild.id)

    @commands.mod_or_permissions(manage_messages=True)
    @speedevent.command(name="stop")
    async def stop_event(self, ctx):
        if ctx.guild.id in self.jobs["guilds"]:
            await self.jobs["guilds"][ctx.guild.id].stop(str(ctx.author))
        else:
            await ctx.send("No speedevents found.")

    @speedevent.command()
    async def join(self, ctx):
        """Join the typing test speed event"""
        if ctx.guild.id in self.jobs["guilds"]:
            await self.jobs["guilds"][ctx.guild.id].join(ctx.author.id, ctx.author.display_name)
        else:
            await ctx.send("Event has not started yet")

    @typerset_check()
    @commands.group()
    async def typerset(self, ctx):
        """Settings for the typing speed test"""

    @commands.guild_only()
    @typerset.command()
    async def time(self, ctx, num: int):
        """Sets the time delay (in seconds) to start a speedtest event (max limit = 1000 seconds)"""
        if num <= 1000 and num >= 10:
            await self.config.guild_from_id(ctx.guild.id).time_start.set(num)
            await ctx.send(f"Changed delay to {num}")
        else:
            await ctx.send("The Min limit is 10 seconds\nThe Max limit is 1000 seconds")

    @typerset.command()
    async def words(self, ctx, min: int, max: int):
        """Sets the number of minimum and maximum number of words
        Range: min>0 and max<=100"""
        if min > 0 and max <= 100:
            await (
                self.config.guild_from_id(ctx.guild.id).text_size.set((min, max))
                if ctx.guild
                else self.config.user_from_id(ctx.author.id).text_size.set((min, max))
            )
            await ctx.send(f"The number of words are changed to\nMinimum:{min}\nMaximum:{max}")
        else:
            await ctx.send(
                "The minimum number of words must be greater than 0\nThe maxiumum number of words must be less than or equal to 100 "
            )

    @commands.guild_only()
    @typerset.command()
    async def dm(self, ctx, toggle: bool):
        """Toggle whether the bot should send analytics in the dm or not
        Toggles available: false, true"""
        await self.config.guild_from_id(ctx.guild.id).dm.set(toggle)
        await ctx.send(f"I will {'' if toggle else 'not'} send the speedevent analytics in dms")

    @typerset.command(name="type")
    async def type_of_text(self, ctx, type_txt: str):
        """Set the type of text to generate.
        Types available: lorem, gibberish"""
        check = ("lorem", "gibberish")
        if type_txt in check:
            await (
                self.config.guild_from_id(ctx.guild.id).type.set(type_txt)
                if ctx.guild
                else self.config.user_from_id(ctx.author.id).type.set(type_txt)
            )
            await ctx.send(f"Changed type to {type_txt}")
        else:
            await ctx.send("Only two valid types available: gibberish,lorem")

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
