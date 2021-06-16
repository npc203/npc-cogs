import asyncio
import contextlib
import time

from discord import NotFound
from tabulate import tabulate

from .utils import evaluate, get_text, nocheats


class Speedevent:
    def __init__(self, ctx, countdown, settings, all=False):
        self.ctx = ctx
        self.countdown = countdown
        self.settings = settings
        self.joined = {ctx.author.id: ctx.author.display_name} if not all else dict()
        self.tasks = {}
        self.event_started = False
        self.leaderboard = []
        self.all = all
        self.finished = 0
        self.bot_msg = None
        # if all means, everyone are enrolled in the speedevent
        self.check = (
            (lambda msg: msg.author.id not in self.joined)
            if all
            else (lambda msg: msg.author.id in self.joined)
        )

    async def start(self):
        self.a_string, status_code = await get_text(self.settings)
        if not status_code:
            await self.ctx.send("Something went wrong while getting the text")
            return
        self.tasks["event"] = asyncio.create_task(self.task_event_race())

        iscancelled = False
        try:
            await self.tasks["event"]
        except asyncio.CancelledError:
            iscancelled = True

        if self.leaderboard:
            await self.ctx.send(
                "```Event results:\n{}```".format(
                    tabulate(
                        sorted(self.leaderboard, key=lambda x: x[2], reverse=True),
                        headers=("Name", "Time taken", "WPM", "Mistakes"),
                        tablefmt="fancy_grid",
                    )
                )
            )
        elif not iscancelled:
            await self.ctx.send("No one was brave enough to complete the test 😦")

    async def stop(self, name):
        for task in self.tasks.values():
            task.cancel()

        await self.ctx.send(f"{name} ended the speedevent")

    async def join(self, user_id, nick):
        if self.event_started:
            return await self.ctx.send("Sorry event already started and ongoing")

        if self.all:
            notify = await self.ctx.send("This event is open for all, You don't need to join in")
        elif user_id in self.joined:
            notify = await self.ctx.send("You already joined in")
        else:
            self.joined[user_id] = nick
            notify = await self.ctx.send(f"{nick} has joined in")

        perms = notify.channel.permissions_for(self.ctx.me)
        # Delete the message
        await asyncio.sleep(2)
        if perms.manage_messages:
            with contextlib.suppress(NotFound):
                await notify.delete()

    async def final_evaluate(self, msg_result, time_fin):
        if self.check(msg_result):
            if results := await evaluate(
                self.ctx,
                self.a_string,
                msg_result.content,
                time_fin,
                msg_result.author.id if self.settings["dm"] else None,
                author_name=msg_result.author.display_name,
            ):
                results.insert(0, str(msg_result.author))
                self.leaderboard.append(results)
            if self.all:
                self.joined[msg_result.author.id] = True
            else:
                self.joined.pop(msg_result.author.id)

    async def task_event_race(self):
        """Event Race"""
        active = "\n".join(
            [f"{index}. {self.joined[user]}" for index, user in enumerate(self.joined, 1)]
        )
        countdown = await self.ctx.send(
            f"A Typing speed test event will commence in {self.countdown} seconds\n"
            + (
                f" Type `{self.ctx.prefix}speedevent join` to enter the race\n "
                + f"Joined Users:\n{active}"
                if not self.all
                else ""
            )
        )
        await asyncio.sleep(5)
        for i in range(self.countdown - 5, 5, -5):
            active = "\n".join(
                [f"{index}. {self.joined[user]}" for index, user in enumerate(self.joined, 1)]
            )
            await countdown.edit(
                content=f"A Typing speed test event will commence in {i} seconds\n"
                + (
                    f" Type `{self.ctx.prefix}speedevent join` to enter the race\n "
                    + f"Joined Users:\n{active}"
                    if not self.all
                    else ""
                )
            )
            await asyncio.sleep(5)
        await countdown.delete()

        if len(self.joined) <= 1 and not self.all:
            await self.ctx.send("Oh no, looks like nobody joined the speedevent")
            raise asyncio.CancelledError

        msg = await self.ctx.send("Speedevent Starts in 5")
        for i in range(4, 0, -1):
            await asyncio.sleep(1)
            await msg.edit(content=f"Speedevent Starts in {i}")

        self.tasks["sticky"] = asyncio.create_task(
            self.sticky(f"Write the given paragraph\n```{nocheats(self.a_string)}```")
        )

        match_begin = time.perf_counter()
        self.event_started = True

        async def runner():
            while True:
                msg_result = await self.ctx.bot.wait_for(
                    "message",
                    timeout=180.0,
                    check=lambda msg: not msg.author.bot and msg.channel.id == self.ctx.channel.id,
                )

                self.finished += 1
                asyncio.create_task(
                    self.final_evaluate(msg_result, time.perf_counter() - match_begin)
                )
                if not self.all and len(self.joined) == 0:
                    break

        try:
            await asyncio.wait_for(runner(), timeout=180)
        except asyncio.TimeoutError:
            pass

    async def sticky(self, text):
        content = ("Remaing time: 180 seconds\n" if self.all else "") + text
        msg = await self.ctx.send(content)

        fin = 180
        cont = time.time()
        while fin > 0:
            if self.finished > 6:
                self.finished = 0
                await msg.delete()
                msg = await self.ctx.send(content)
            elif self.all and time.time() - cont > 5:
                fin -= 5
                content = (f"Remaing time: {fin} seconds\n" if self.all else "") + text
                await msg.edit(content=content)
                cont = time.time()

            await asyncio.sleep(1)
