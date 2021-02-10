import asyncio
import contextlib
import time

from discord import NotFound
from tabulate import tabulate

from .utils import evaluate, get_text, nocheats


class Speedevent:
    def __init__(self, ctx, countdown, settings):
        self.ctx = ctx
        self.countdown = countdown
        self.settings = settings
        self.joined = {ctx.author.id: ctx.author.display_name}
        self.event_started = False
        self.leaderboard = []

    async def start(self):
        a_string, status_code = await get_text(self.settings, self.ctx.guild.id)
        if not status_code:
            await self.ctx.send("Something went wrong while getting the text")
            return
        self.event = asyncio.create_task(self.task_event_race(a_string))
        await self.event
        if self.leaderboard:
            await self.ctx.send(
                "```Event results:\n{}```".format(
                    tabulate(
                        self.leaderboard,
                        headers=("Name", "Time taken", "WPM", "Mistakes"),
                        tablefmt="fancy_grid",
                    )
                )
            )
        else:
            await self.ctx.send("No one was brave enough to complete the test 😦")

    async def join(self, user_id, nick):
        if self.event_started:
            return await self.ctx.send(f"Sorry event already started and ongoing")
        if user_id in self.joined:
            notify = await self.ctx.send(f"You already joined in")
        else:
            self.joined[user_id] = nick
            notify = await self.ctx.send(f"{nick} has joined in")

        perms = notify.channel.permissions_for(self.ctx.me)
        # Delete the message
        await asyncio.sleep(2)
        if perms.manage_messages:
            with contextlib.suppress(NotFound):
                await notify.delete()

    async def task_event_race(self, a_string):
        """Event Race"""
        active = "\n".join(
            [f"{index}. {self.joined[user]}" for index, user in enumerate(self.joined, 1)]
        )
        countdown = await self.ctx.send(
            f"A Typing speed test event will commence in {self.countdown} seconds\n"
            f" Type `{self.ctx.clean_prefix}speedevent join` to enter the race\n "
            f"Joined Users:\n{active}"
        )
        await asyncio.sleep(5)
        for i in range(self.countdown - 5, 0, -5):  # TODO add to config, time to start event
            active = "\n".join(
                [f"{index}. {self.joined[user]}" for index, user in enumerate(self.joined, 1)]
            )
            await countdown.edit(
                content=f"A Typing speed test event will commence in {i} seconds\n"
                f" Type `{self.ctx.clean_prefix}speedevent join` to enter the race\n "
                f"Joined Users:\n{active}"
            )
            await asyncio.sleep(5)
        await countdown.delete()
        await self.ctx.send(content=f"Write the given paragraph\n```{nocheats(a_string)}```")
        match_begin = time.time()
        self.event_started = True

        async def runner():
            while True:
                msg_result = await self.ctx.bot.wait_for(
                    "message",
                    timeout=180.0,
                    check=lambda msg: msg.author.id in self.joined,
                )
                self.joined.pop(msg_result.author.id)
                results = await evaluate(
                    self.ctx,
                    a_string,
                    msg_result.content,
                    time.time() - match_begin,
                    msg_result.author.id if self.settings["dm"] else None,
                    author_name=msg_result.author.display_name,
                )
                if results:
                    results.insert(0, msg_result.author.name)
                    self.leaderboard.append(results)
                if len(self.joined) == 0:
                    break

        try:
            await asyncio.wait_for(runner(), timeout=180)
        except asyncio.TimeoutError:
            pass
