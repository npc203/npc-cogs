# This contains a bunch of utils


from typing import Optional

from redbot.core.utils.chat_formatting import humanize_timedelta

# From dpy server >.<
EMOJI_REGEX = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
# https://www.w3resource.com/python-exercises/re/python-re-exercise-42.php
LINK_REGEX = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"


def emoji_converter(bot, emoji) -> Optional[str]:
    """General emoji converter"""
    # TODO find a way to detect unicode emojis properly
    if not emoji:
        return
    if isinstance(emoji, int) or emoji.isdigit():
        return bot.get_emoji(int(emoji))
    emoji = emoji.strip()
    return emoji


# Taken from the core help as well :)
def shorten_line(a_line: str) -> str:
    if len(a_line) < 70:  # embed max width needs to be lower
        return a_line
    return a_line[:67] + "..."


# Add permissions
def get_perms(command):
    final_perms = ""
    neat_format = lambda x: " ".join(i.capitalize() for i in x.replace("_", " ").split())

    user_perms = []
    if perms := getattr(command.requires, "user_perms"):
        user_perms.extend(neat_format(i) for i, j in perms if j)
    if perms := command.requires.privilege_level:
        if perms.name != "NONE":
            user_perms.append(neat_format(perms.name))

    if user_perms:
        final_perms += "User Permission(s): " + ", ".join(user_perms) + "\n"

    if perms := getattr(command.requires, "bot_perms"):
        if perms_list := ", ".join(neat_format(i) for i, j in perms if j):
            final_perms += "Bot Permission(s): " + perms_list

    return final_perms


# Add cooldowns
def get_cooldowns(command):
    cooldowns = []
    if s := command._buckets._cooldown:
        txt = f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)}"
        try:
            txt += f" per {s.type.name.capitalize()}"
        # This is to avoid custom bucketype erroring out stuff (eg:licenseinfo)
        except AttributeError:
            pass
        cooldowns.append(txt)

    if s := command._max_concurrency:
        cooldowns.append(f"Max concurrent uses: {s.number} per {s.per.name.capitalize()}")

    return cooldowns


# Add aliases
def get_aliases(command, original):
    if alias := list(command.aliases):
        if original in alias:
            alias.remove(original)
            alias.append(command.name)
        return alias


async def get_category_page_mapper_chunk(
    formatter, get_pages, ctx, cat, help_settings, page_mapping
):
    # Make sure we're not getting the pages (eg: when home button is clicked) else gen category pages
    if not get_pages:
        if cat_page := await formatter.format_category_help(
            ctx, cat, help_settings=help_settings, get_pages=True
        ):
            page_mapping[cat] = cat_page
        else:
            return False
    return True
