import asyncio
import time

from .utils import evaluate, get_text, nocheats


class Single:
    """Single personal typing test stuff"""

    def __init__(self, ctx, settings):
        self.ctx = ctx
        self.settings = settings

    async def start(self):
        """Start the test, Display the question and get result"""
        async with self.ctx.typing():
            a_string, status_code = await get_text(self.settings, self.ctx.guild.id)
        if status_code:
            self.task = asyncio.create_task(self.task_personal_race(self.ctx, a_string))
        else:
            return
        try:
            time_taken, b_string = await self.task
            await evaluate(self.ctx, a_string, b_string, time_taken, None)
        except asyncio.CancelledError:
            return await self.ctx.send("Cancelled typing test")

    async def cancel(self):
        # Maybe make this function not async?
        self.task.cancel()

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
                await ctx.bot.wait_for(
                    "message",
                    timeout=300.0,
                    check=lambda m: m.author.id == ctx.author.id,
                )
            ).content.strip()
        except asyncio.TimeoutError:
            await msg.edit(content="Sorry you were way too slow, timed out")
            return
        end = time.time()
        time_taken = end - start
        return time_taken, b_string
