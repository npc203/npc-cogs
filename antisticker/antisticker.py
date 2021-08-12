from typing import Literal, Union

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config


class AntiSticker(commands.Cog):
    """
    Prevent stickers from being posted in channels
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=3782421,
            force_registration=True,
        )

    @commands.Cog.listener("on_message_without_command")
    async def runner(self, msg):
        pass

    @commands.command(name="antisticker")
    async def a(self):
        """Prevent stickers from being posted"""

    @a.command()
    async def add(self, ctx, channel_or_all: Union[discord.TextChannel, str]):
        """Add channels to add to the list, or type all to enable every channel"""

    @a.command()
    async def remove(self, ctx, channel: discord.TextChannel):
        """Remove channels from the list"""

    @a.command()
    async def show(self, ctx):
        """Show all settings related to the server"""

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        return
