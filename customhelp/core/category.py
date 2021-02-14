import contextlib
from typing import Optional

import discord

from redbot.core import commands
from redbot.core.commands.help import HelpSettings
from redbot.core.utils.menus import menu, next_page, prev_page, start_adding_reactions

# Keeping all global vars in one place
GLOBAL_CATEGORIES = []
ARROWS = {
    "right": "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}",
    "left": "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
    "cross": "\N{CROSS MARK}",
    "home": "\U0001f3d8\U0000fe0f",
}


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
