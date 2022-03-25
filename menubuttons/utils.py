from dataclasses import dataclass

import discord
import yaml
from redbot.core.utils.chat_formatting import box


@dataclass
class Arrow:
    emoji: discord.Emoji
    label: str
    style: str


async def emoji_converter(bot, emoji: discord.Emoji):
    pass


def quick_emoji_converter(bot, emoji: str):
    pass


async def parse_yaml(ctx, content):
    """Parse the yaml with basic structure checks"""
    # TODO make this as an util function?
    try:
        parsed_data = yaml.safe_load(content)
    except (yaml.parser.ParserError, yaml.constructor.ConstructorError):  # type: ignore
        await ctx.send("Wrongly formatted")
        return
    except yaml.scanner.ScannerError as e:  # type: ignore
        await ctx.send(box(str(e).replace("`", "\N{ZWSP}`")))
        return
    if type(parsed_data) != dict:
        await ctx.send("Invalid Format, Missed a colon probably")
        return

    # TODO pls get a better type checking method
    for i in parsed_data:
        if type(parsed_data[i]) != list:
            await ctx.send("Invalid Format, Likely added unwanted spaces")
            return
    return parsed_data
