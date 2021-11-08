from typing import Optional

from redbot.core import commands
from dataclasses import dataclass

from . import GLOBAL_CATEGORIES


@dataclass
class Category:
    name: str
    desc: str
    cogs: list
    reaction: Optional[str] = None
    long_desc: Optional[str] = None
    thumbnail: Optional[str] = None

    def __eq__(self, item):
        return item == self.name


@dataclass(frozen=True)
class Arrow:
    name: str
    emoji: str
    text: str
    style: str

    def __eq__(self, item):
        return item == self.name


# Helpers
def get_category(category: str) -> Optional[Category]:
    for x in GLOBAL_CATEGORIES:
        if x.name == category:
            return x


class CategoryConvert(commands.Converter):
    async def convert(self, ctx, value: str):
        category = get_category(value)
        if category is not None:
            return category
        raise commands.BadArgument()
