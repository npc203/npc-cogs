from typing import Optional

from redbot.core import commands

from . import GLOBAL_CATEGORIES


class Category:
    def __init__(
        self,
        name: str,
        desc: str,
        cogs: list,
        reaction: str = None,
        long_desc: str = None,
    ):
        self.name = name
        self.desc = desc
        self.long_desc = long_desc
        self.cogs = cogs
        self.reaction = reaction

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
