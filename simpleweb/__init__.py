import json
from pathlib import Path

from redbot.core.bot import Red
from redbot.core.errors import CogLoadError

from .simpleweb import SimpleWeb

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    if not bot.rpc_enabled:
        raise CogLoadError("RPC is not enabled.")
    cog = SimpleWeb(bot)
    await cog.cog_load()
    bot.add_cog(cog)
