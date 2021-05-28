import asyncio

import discord
from redbot.vendored.discord.ext import menus

from .game import Game

TRANS = {
    0: ":black_large_square:",
    "x": ":regional_indicator_x:",
    "o": ":o2:",  # these aren't unicodes cause placing them side by side combines them into something horrible
}


class BoardMenu(menus.Menu):
    def __init__(self, p1: tuple, p2: tuple, isembed: bool, **kwargs):
        super().__init__(**kwargs)
        self.players = [
            (p1[0], "x", p1[1]),
            (p2[0], "o", p2[1]),
        ]
        self.turn = 0  # 0 = player 1,  1 = player 2
        self.game = Game(True)
        self.isembed = isembed

        mapper = [
            ["\N{NORTH WEST ARROW}", "\N{UPWARDS BLACK ARROW}", "\N{NORTH EAST ARROW}"],
            [
                "\N{LEFTWARDS BLACK ARROW}",
                "\N{BLACK CIRCLE FOR RECORD}",
                "\N{BLACK RIGHTWARDS ARROW}",
            ],
            ["\N{SOUTH WEST ARROW}", "\N{DOWNWARDS BLACK ARROW}", "\N{SOUTH EAST ARROW}"],
        ]

        def func_gen(emoji, ind):
            async def ret_func(self, payload):
                self.game.move(ind, self.players[self.turn][1])
                await self.message.edit(**self.edit_board())
                self.turn = 0 if self.turn else 1

            return menus.Button(emoji, ret_func)

        for i in range(3):
            for j in range(3):
                self.add_button(func_gen(mapper[i][j], (i, j)))

        async def on_stop(self, payload):
            self.stop()

        self.add_button(menus.Button("⏹️", on_stop))

    def edit_board(self):
        board = "\n".join("".join(map(lambda x: TRANS[x], i)) for i in self.game.board)
        return {"content": board}
        """
        if self.isembed:
            emb = discord.Embed(title="Tic Tac Toe")
            emb.add_field(name="\N{ZWSP}", value=board, inline=False)
            emb.add_field(name="Player 1 : :regional_indicator_x:", value=self.players[0][2])
            emb.add_field(name="Player 2 : :o2:", value=self.players[1][2])
            return {"embed": emb}
        else:
            return {"content": board}
        """

    async def send_initial_message(self, ctx, channel):
        return await ctx.send(**self.edit_board())

    def reaction_check(self, payload):
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in map(lambda x: x[0], self.players):
            return False

        if self.players[self.turn][0] != payload.user_id:
            return False

        return payload.emoji in self.buttons