import asyncio

import discord
from redbot.vendored.discord.ext import menus
from redbot_ext_menus import ViewMenu

from .game import Game

TRANS = {
    0: "\N{BLACK LARGE SQUARE}",
    1: "\N{RED APPLE}",
    2: "\N{LARGE GREEN CIRCLE}",
    3: "\N{LARGE GREEN SQUARE}",
}

GET_DIR = {
    "w": "up",
    "s": "down",
    "a": "left",
    "d": "right",
    None: "Click on a reaction to start",
}


# The locks part to sync was inspired by some stackoverflow post which I forgot by now
# Will add the credit if I find it again
class BoardMenu(ViewMenu):
    def __init__(self, player_name, **kwargs):
        super().__init__(**kwargs)
        self.cur_dir = None
        self.player_name = player_name
        self.game = Game(12)
        # maybe use lock here instead of event?
        self.is_started = asyncio.Event()

    def edit_board(self, end=False):
        emb = discord.Embed(title="Snake", description=self.make_board())
        emb.add_field(name="Score", value=self.game.score)
        emb.add_field(name="Player", value=self.player_name)
        if end:
            emb.add_field(name="Current Direction", value="Game Ended")
        else:
            emb.add_field(name="Current Direction", value=GET_DIR[self.cur_dir])
        return emb

    def make_board(self):
        return "\n".join("".join(map(lambda x: TRANS[x], i)) for i in self.game.board)

    async def loop(self):
        await self.is_started.wait()
        while True:
            await asyncio.sleep(1.2)
            if not self.game.move(self.cur_dir):
                await self.message.edit(embed=self.edit_board(end=True))
                break
            await self.message.edit(embed=self.edit_board())
        self.stop()

    async def send_initial_message(self, ctx, channel):
        self.task = ctx.bot.loop.create_task(self.loop())
        return await self.send_with_view(channel, embed=self.edit_board())

    @menus.button("⬆️")
    async def up(self, payload):
        self.cur_dir = "w"
        self.is_started.set()

    @menus.button("⬇️")
    async def down(self, payload):
        self.cur_dir = "s"
        self.is_started.set()

    @menus.button("⬅️")
    async def left(self, payload):
        self.cur_dir = "a"
        self.is_started.set()

    @menus.button("➡️")
    async def right(self, payload):
        self.cur_dir = "d"
        self.is_started.set()

    @menus.button("⏹️")
    async def on_stop(self, payload):
        self.task.cancel()
        await self.message.edit(embed=self.edit_board(end=True))
        self.stop()
