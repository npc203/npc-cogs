import asyncio
import re
from collections import namedtuple
from itertools import chain
from typing import AsyncIterator, Iterable, List, Literal, Union, cast

import discord
import tabulate

from redbot.core import checks, commands
from redbot.core.commands.context import Context
from redbot.core.commands.help import (
    HelpSettings,
    NoCommand,
    NoSubCommand,
    dpy_commands,
    mass_purge,
)
from redbot.core.i18n import Translator
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import box, humanize_timedelta, pagify

from .category import *
from .utils import *

HelpTarget = Union[
    commands.Command,
    commands.Group,
    commands.Cog,
    CategoryConvert,
    dpy_commands.bot.BotBase,
    str,
]

EmbedField = namedtuple("EmbedField", "name value inline")
EMPTY_STRING = "\N{ZERO WIDTH SPACE}"

_ = Translator("Help", __file__)

# Note to anyone reading this, This is the default formatter deffo, just slightly edited.
class BaguetteHelp(commands.RedHelpFormatter):
    """In the memory of Jack the virgin"""

    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    @staticmethod
    async def parse_command(ctx, help_for: str):
        """
        Handles parsing
        """

        maybe_cog = ctx.bot.get_cog(help_for)
        if maybe_cog:
            return maybe_cog

        maybe_cateory = get_category(help_for)
        if maybe_cateory:
            return maybe_cateory

        # TODO does this wreck havoc?
        if alias_cog := ctx.bot.get_cog("Alias"):
            alias_name = help_for
            alias = await alias_cog._aliases.get_alias(ctx.guild, alias_name=alias_name)
            if alias:
                help_for = alias.command

        com = ctx.bot
        last = None

        clist = help_for.split()

        for index, item in enumerate(clist):
            try:
                com = com.all_commands[item]
                # TODO: This doesn't handle valid command aliases.
                # swap parsing method to use get_command.
            except (KeyError, AttributeError):
                if last:
                    raise NoSubCommand(last=last, not_found=clist[index:]) from None
                else:
                    raise NoCommand() from None
            else:
                last = com
        # This does take an extra 0.1 seconds to complete. but worth it?
        if alias:
            com_alias = com.copy()
            com_alias.parent = None
            com_alias.cog = com.cog
            com_alias.name = alias_name
            com_alias.aliases.append(com.qualified_name)
            return com_alias
        return com

    async def get_category_help_mapping(self, ctx, category, help_settings: HelpSettings):
        # TODO getting every cog and checking if its in category isn't optimised.
        sorted_iterable = []
        isuncategory = False
        if category.name == GLOBAL_CATEGORIES[-1].name:
            isuncategory = True
        for cogname, cog in (*sorted(ctx.bot.cogs.items()), (None, None)):
            # TODO test this if condition, cause i can't trust my math
            if (cogname in category.cogs) or (isuncategory and cogname == None):
                cm = await self.get_cog_help_mapping(ctx, cog, help_settings=help_settings)
                if cm:
                    sorted_iterable.append((cogname, cm))
        return sorted_iterable

    async def send_help(
        self,
        ctx: Context,
        help_for: HelpTarget = None,
        *,
        from_help_command: bool = False,
    ):
        """
        This delegates to other functions.

        For most cases, you should use this and only this directly.
        """

        help_settings = await HelpSettings.from_context(ctx)

        if help_for is None or isinstance(help_for, dpy_commands.bot.BotBase):
            await self.format_bot_help(ctx, help_settings=help_settings)
            return

        if isinstance(help_for, str):
            try:
                help_for = await self.parse_command(ctx, help_for)
            except NoCommand:
                await self.command_not_found(ctx, help_for, help_settings=help_settings)
                return
            except NoSubCommand as exc:
                if help_settings.verify_exists:
                    await self.subcommand_not_found(
                        ctx, exc.last, exc.not_found, help_settings=help_settings
                    )
                    return
                help_for = exc.last

        if isinstance(help_for, commands.Cog):
            await self.format_cog_help(ctx, help_for, help_settings=help_settings)
        elif isinstance(help_for, Category):
            await self.format_category_help(ctx, help_for, help_settings=help_settings)
        else:
            await self.format_command_help(ctx, help_for, help_settings=help_settings)

    async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings):
        coms = await self.get_cog_help_mapping(ctx, obj, help_settings=help_settings)
        if not (coms or help_settings.verify_exists):
            return

        description = obj.format_help_for_context(ctx)
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)

        if await ctx.embed_requested():
            emb = {
                "embed": {"title": "", "description": ""},
                "footer": {"text": ""},
                "fields": [],
            }

            emb["footer"]["text"] = tagline
            if description:
                splitted = description.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                if not value:
                    value = EMPTY_STRING
                field = EmbedField(f"{name[:252]}", value[:1024], False)
                emb["fields"].append(field)

            if coms:

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67] + "..."

                command_text = "\n".join(
                    shorten_line(f"`{name:<15}:`{command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(coms.items())
                )
                for i, page in enumerate(pagify(command_text, page_length=500, shorten_by=0)):
                    if i == 0:
                        title = _("**__Commands:__**")
                    else:
                        title = _("**__Commands:__** (continued)")
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            await self.send_pages(ctx, pages, embed=True, help_settings=help_settings)

        else:
            # TODO remove this?
            subtext = None
            subtext_header = None
            if coms:
                subtext_header = _("Commands:")
                max_width = max(discord.utils._string_width(name) for name in coms.keys())

                def width_maker(cmds):
                    doc_max_width = 80 - max_width
                    for nm, com in sorted(cmds):
                        width_gap = discord.utils._string_width(nm) - len(nm)
                        doc = com.format_shortdoc_for_context(ctx)
                        if len(doc) > doc_max_width:
                            doc = doc[: doc_max_width - 3] + "..."
                        yield nm, doc, max_width - width_gap

                subtext = "\n".join(
                    f"  {name:<{width}} {doc}" for name, doc, width in width_maker(coms.items())
                )

            to_page = "\n\n".join(filter(None, (description, subtext_header, subtext)))
            pages = [box(p) for p in pagify(to_page)]
            await self.send_pages(ctx, pages, embed=False, help_settings=help_settings)

    async def format_category_help(
        self,
        ctx: Context,
        obj: CategoryConvert,
        help_settings: HelpSettings,
        get_pages: bool = False,
    ):
        coms = await self.get_category_help_mapping(ctx, obj, help_settings=help_settings)
        if not coms:
            return

        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)

        if await ctx.embed_requested():

            emb = {
                "embed": {"title": "", "description": ""},
                "footer": {"text": ""},
                "fields": [],
            }

            emb["footer"]["text"] = tagline
            if description:
                emb["embed"]["description"] = f"*{description[:250]}*"

            all_cog_text = ""
            for cog_name, data in coms:
                cog_text = "\n" + "\n".join(
                    f"`{name:<15}:`{command.format_shortdoc_for_context(ctx)[:140]}"  # No more than 2 lines of desc (140 = 2 lines max embed line width)
                    for name, command in sorted(data.items())
                )
                all_cog_text += cog_text
            all_cog_text = "\n".join(sorted(all_cog_text.split("\n")))
            title = obj.name.capitalize()
            for i, page in enumerate(pagify(all_cog_text, page_length=500, shorten_by=0)):
                field = EmbedField(title, page, False)
                emb["fields"].append(field)
                title = EMPTY_STRING

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            if get_pages:
                return pages
            else:
                await self.send_pages(ctx, pages, embed=True, help_settings=help_settings)
        else:
            # fix this
            await ctx.send("Kindly enable embeds")

    async def format_command_help(
        self, ctx: Context, obj: commands.Command, help_settings: HelpSettings
    ):

        send = help_settings.verify_exists
        if not send:
            async for __ in self.help_filter_func(
                ctx, (obj,), bypass_hidden=True, help_settings=help_settings
            ):
                send = True

        if not send:
            return

        command = obj

        description = command.description or ""

        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        signature = _(
            "`Syntax: {ctx.clean_prefix}{command.qualified_name} {command.signature}`"
        ).format(ctx=ctx, command=command)
        subcommands = None

        if hasattr(command, "all_commands"):
            grp = cast(commands.Group, command)
            subcommands = await self.get_group_help_mapping(ctx, grp, help_settings=help_settings)

        if await ctx.embed_requested():
            emb = {
                "embed": {"title": "", "description": ""},
                "footer": {"text": ""},
                "fields": [],
            }

            if description:
                emb["embed"]["title"] = f"*{description[:250]}*"

            emb["footer"]["text"] = tagline
            emb["embed"]["description"] = signature

            command_help = command.format_help_for_context(ctx)
            if command_help:
                splitted = command_help.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                if not value:
                    value = EMPTY_STRING
                field = EmbedField("Description", name[:250] + "\n" + value[:1024], False)
                emb["fields"].append(field)

                # Add aliases
                if alias := command.aliases:
                    if ctx.invoked_with in alias:
                        alias.remove(ctx.invoked_with)
                        alias.append(command.name)
                    emb["fields"].append(EmbedField("Aliases", ",".join(alias), False))

                # Add permissions
                get_list = ["user_perms", "bot_perms"]
                final_perms = []
                neat_format = lambda x: " ".join(
                    i.capitalize() for i in x.replace("_", " ").split()
                )
                for thing in get_list:
                    if perms := getattr(command.requires, thing):
                        perms_list = [
                            neat_format(i) for i, j in perms if j
                        ]  # TODO pls learn more to fix this
                        if perms_list:
                            final_perms += perms_list
                if perms := command.requires.privilege_level:
                    if perms.name != "NONE":
                        final_perms.append(neat_format(perms.name))
                if final_perms:
                    emb["fields"].append(EmbedField("Permissions", ", ".join(final_perms), False))

                # Add cooldowns
                cooldowns = []
                if s := command._buckets._cooldown:
                    cooldowns.append(
                        f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)} per {s.type.name.capitalize()}"
                    )
                if s := command._max_concurrency:
                    cooldowns.append(
                        f"Max concurrent uses: {s.number} per {s.per.name.capitalize()}"
                    )
                if cooldowns:
                    emb["fields"].append(EmbedField("Cooldowns:", "\n".join(cooldowns), False))

            if subcommands:

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67] + ".."

                subtext = "\n" + "\n".join(
                    shorten_line(f"`{name:<15}:`{command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(subcommands.items())
                )
                for i, page in enumerate(pagify(subtext, page_length=500, shorten_by=0)):
                    if i == 0:
                        title = _("**__Subcommands:__**")
                    else:
                        title = _(EMPTY_STRING)
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)
            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            await self.send_pages(ctx, pages, embed=True, help_settings=help_settings)
        else:
            await ctx.send("Enable embeds pls")

    async def format_bot_help(
        self, ctx: Context, help_settings: HelpSettings, get_pages: bool = False
    ):
        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        if not await ctx.embed_requested():  # Maybe redirect to non-embed minimal format
            await ctx.send("You need to enable embeds to use custom help menu")
        else:
            emb = {
                "embed": {"title": "", "description": ""},
                "footer": {"text": ""},
                "fields": [],
            }

            emb["footer"]["text"] = tagline
            if description:
                splitted = description.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                if not value:
                    value = EMPTY_STRING
                field = EmbedField(name[:252], value[:1024], False)
                emb["fields"].append(field)

            category_text = ""
            emb["title"] = f"{ctx.me.name} Help Menu"
            for i in pagify(
                "\n".join(
                    [
                        f"{cat.reaction if cat.reaction else ''} `{ctx.clean_prefix}help {cat.name:<10}:`**{cat.desc}**\n"
                        for cat in GLOBAL_CATEGORIES
                        if cat.cogs
                    ]
                ),
                page_length=1018,
            ):
                emb["fields"].append(EmbedField("Categories:", i, False))

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            if get_pages:
                return pages
            else:
                await self.send_pages(
                    ctx,
                    pages,
                    embed=True,
                    help_settings=help_settings,
                    add_emojis=((await self.config.settings())["react"]) and True,
                )

    # TODO maybe try lazy loading
    async def make_embeds(
        self,
        ctx,
        embed_dict: dict,
        help_settings: HelpSettings,
    ):
        """Returns Embed pages (Really copy paste from core)"""
        pages = []
        thumbnail_url = await self.config.settings.thumbnail()
        page_char_limit = help_settings.page_char_limit
        page_char_limit = min(page_char_limit, 5500)
        author_info = {
            "name": _("{ctx.me.display_name} Help Menu").format(ctx=ctx),
            "icon_url": ctx.me.avatar_url,
        }
        offset = len(author_info["name"]) + 20
        foot_text = embed_dict["footer"]["text"]
        if foot_text:
            offset += len(foot_text)
        offset += len(embed_dict["embed"]["description"])
        offset += len(embed_dict["embed"]["title"])
        if page_char_limit + offset > 5500:
            page_char_limit = 5500 - offset
        elif page_char_limit < 250:
            page_char_limit = 250

        field_groups = self.group_embed_fields(embed_dict["fields"], page_char_limit)

        color = await ctx.embed_color()
        page_count = len(field_groups)

        if not field_groups:  # This can happen on single command without a docstring
            embed = discord.Embed(color=color, **embed_dict["embed"])
            embed.set_author(**author_info)
            embed.set_footer(**embed_dict["footer"])
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            pages.append(embed)

        for i, group in enumerate(field_groups, 1):
            embed = discord.Embed(color=color, **embed_dict["embed"])

            if page_count > 1:
                description = _("*Page {page_num} of {page_count}*\n{content_description}").format(
                    content_description=embed.description,
                    page_num=i,
                    page_count=page_count,
                )
                embed.description = description

            embed.set_author(**author_info)

            for field in group:
                embed.add_field(**field._asdict())

            embed.set_footer(**embed_dict["footer"])
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            pages.append(embed)

        return pages

    async def send_pages(
        self,
        ctx: Context,
        pages: List[Union[str, discord.Embed]],
        embed: bool = True,
        help_settings: HelpSettings = None,
        add_emojis: bool = False,
    ):
        """
        Sends pages based on settings.
        """

        # save on config calls
        channel_permissions = ctx.channel.permissions_for(ctx.me)

        if not (channel_permissions.add_reactions and help_settings.use_menus):

            max_pages_in_guild = help_settings.max_pages_in_guild
            use_DMs = len(pages) > max_pages_in_guild
            destination = ctx.author if use_DMs else ctx.channel
            delete_delay = help_settings.delete_delay
            messages: List[discord.Message] = []
            for page in pages:
                try:
                    if embed:
                        msg = await destination.send(embed=page)
                    else:
                        msg = await destination.send(page)
                except discord.Forbidden:
                    return await ctx.send(
                        _(
                            "I couldn't send the help message to you in DM. "
                            "Either you blocked me or you disabled DMs in this server."
                        )
                    )
                else:
                    messages.append(msg)
            if use_DMs and help_settings.use_tick:
                await ctx.tick()
            # The if statement takes into account that 'destination' will be
            # the context channel in non-DM context, reusing 'channel_permissions' to avoid
            # computing the permissions twice.
            if (
                not use_DMs  # we're not in DMs
                and delete_delay > 0  # delete delay is enabled
                and channel_permissions.manage_messages  # we can manage messages here
            ):

                # We need to wrap this in a task to not block after-sending-help interactions.
                # The channel has to be TextChannel as we can't bulk-delete from DMs
                async def _delete_delay_help(
                    channel: discord.TextChannel,
                    messages: List[discord.Message],
                    delay: int,
                ):
                    await asyncio.sleep(delay)
                    await mass_purge(messages, channel)

                asyncio.create_task(_delete_delay_help(destination, messages, delete_delay))
        else:
            # Specifically ensuring the menu's message is sent prior to returning
            m = await (ctx.send(embed=pages[0]) if embed else ctx.send(pages[0]))
            c = dict(
                menus.DEFAULT_CONTROLS if len(pages) > 1 else {"\N{CROSS MARK}": menus.close_menu}
            )
            # TODO important!
            if add_emojis:
                # Adding additional category emojis , regex from dpy server
                for cat in GLOBAL_CATEGORIES:
                    if cat.reaction:
                        match = re.search(
                            EMOJI_REGEX,
                            cat.reaction,
                        )
                        if emj := (
                            self.bot.get_emoji(int(match.group("id"))) if match else cat.reaction
                        ):
                            c[emj] = react_page
                c["\U0001f3d8\U0000fe0f"] = home_page
            # Allow other things to happen during menu timeout/interaction.
            asyncio.create_task(menus.menu(ctx, pages, c, message=m))
            # menu needs reactions added manually since we fed it a message
            menus.start_adding_reactions(m, c.keys())
