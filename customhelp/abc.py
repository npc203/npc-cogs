from abc import ABC, abstractmethod
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context


# TODO Need to enforce this on themes.
class ThemesMeta(ABC):
    @abstractmethod
    async def format_cog_help(
        self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings
    ):
        raise NotImplementedError

    @abstractmethod
    async def format_command_help(
        self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings
    ):
        raise NotImplementedError

    @abstractmethod
    async def format_bot_help(self, ctx: Context, help_settings: HelpSettings):
        raise NotImplementedError

    @abstractmethod
    async def command_not_found(self, ctx: Context, help_settings: HelpSettings):
        raise NotImplementedError