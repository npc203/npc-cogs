from redbot.core import commands
import datetime
from .socketstatsmenu import *
from collections import Counter
from redbot.core.utils import AsyncIter
from tabulate import tabulate


class Wss(commands.Cog):
    """STOP INSTALLING THIS, THIS IS FIXATOR'S SCRIPT THAT I JUST SKIDDED"""

    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "socket_stats"):
            bot.socket_stats = Counter()

    @commands.Cog.listener()
    async def on_socket_response(self, msg):
        self.bot.socket_stats[msg.get("t", "UNKNOWN") or "UNDEFINED"] += 1

    @commands.command(aliases=["wsstats"], hidden=True)
    @commands.bot_has_permissions(embed_links=True, external_emojis=True)
    async def socketstats(self, ctx, add_chart: bool = False):
        """WebSocket stats."""
        delta = datetime.datetime.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        chart = None
        if not await self.bot.is_owner(ctx.author):
            add_chart = False
        if add_chart:
            chart = await self.bot.loop.run_in_executor(
                None, create_counter_chart, self.bot.socket_stats, "Socket events"
            )
        await WSStatsMenu(
            WSStatsPager(
                AsyncIter(
                    chat.pagify(
                        tabulate(
                            [
                                (n, chat.humanize_number(v), v / minutes)
                                for n, v in self.bot.socket_stats.most_common()
                            ],
                            headers=["Event", "Count", "APM"],
                            floatfmt=".2f" if add_chart else ".5f",
                        ),
                        page_length=2039,
                    )
                ),
                add_image=add_chart,
            ),
            header=f"{chat.humanize_number(total)} socket events observed (<:apm:677494331166425128> {cpm:.2f}):",
            image=chart,
        ).start(ctx)
