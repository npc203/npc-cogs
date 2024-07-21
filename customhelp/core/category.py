from dataclasses import asdict, dataclass
from typing import Optional

import discord
from redbot.core import commands

from . import GLOBAL_CATEGORIES


@dataclass
class Category:
    name: str
    desc: str
    cogs: list
    is_uncat: bool = False
    reaction: Optional[str] = None
    long_desc: Optional[str] = None
    thumbnail: Optional[str] = None
    label: str = ""
    style: str = "primary"

    def __eq__(self, item):
        return item == self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Arrow:
    name: str
    emoji: str
    label: str
    style: discord.ButtonStyle

    def __eq__(self, item):
        return item == self.name

    def __getitem__(self, item):
        return getattr(self, item, None)

    def keys(self):
        return ("emoji", "label", "style")

    def items(self):
        return {key: getattr(self, key) for key in self.keys()}


# Helpers
def get_category(category: Optional[str]) -> Optional[Category]:
    if not category:
        return

    for x in GLOBAL_CATEGORIES:
        if x.name == category:
            return x


class CategoryConvert(commands.Converter):
    async def convert(self, ctx, value: str):
        category = get_category(value)
        if category is not None:
            return category
        raise commands.BadArgument()
