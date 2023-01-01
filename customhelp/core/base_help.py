import asyncio
from collections import namedtuple
from itertools import chain
from typing import List, Union, cast

import discord
from redbot.core import commands
from redbot.core.commands.context import Context
from redbot.core.commands.help import (
    HelpSettings,
    NoCommand,
    NoSubCommand,
    _,
    dpy_commands,
    mass_purge,
)
from redbot.core.utils.chat_formatting import pagify

from . import ARROWS, GLOBAL_CATEGORIES, get_menu
from .category import Category, get_category
from .dpy_menus import ListPages
from .utils import (
    close_menu,
    emoji_converter,
    first_page,
    get_aliases,
    get_cooldowns,
    get_perms,
    home_page,
    last_page,
    next_page,
    prev_page,
    react_page,
    shorten_line,
)

HelpTarget = Union[
    commands.Command,
    commands.Group,
    commands.Cog,
    Category,
    dpy_commands.bot.BotBase,
    str,
]

EmbedField = namedtuple("EmbedField", "name value inline")
EMPTY_STRING = "\N{ZERO WIDTH SPACE}"


# Note to anyone reading this, This is the default formatter deffo, just slightly edited.
class BaguetteHelp(commands.RedHelpFormatter):
    """In the memory of Jack the virgin"""

    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    @staticmethod
    async def parse_command(ctx, help_for: str) -> HelpTarget:
        """
        Handles parsing
        """

        maybe_cog = ctx.bot.get_cog(help_for)
        if maybe_cog:
            return maybe_cog

        maybe_cateory = get_category(help_for)
        if maybe_cateory:
            return maybe_cateory

        alias = None
        alias_name = None
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
        if alias and alias_name:
            com_alias = com.copy()
            com_alias.parent = None
            com_alias.cog = com.cog
            com_alias.name = alias_name
            com_alias.aliases.append(com.qualified_name)
            return com_alias
        return com

    async def get_category_help_mapping(
        self, ctx, category, help_settings: HelpSettings, bypass_checks=False
    ):
        # Having bypass_checks to prevent triggering self.blacklist many times.
        if not bypass_checks and not await self.blacklist(ctx, category.name):
            return
        sorted_iterable = []
        sorted_cogs = sorted(category.cogs)
        isuncategory = False
        if category.name == GLOBAL_CATEGORIES[-1].name:
            isuncategory = True
            sorted_cogs.append(None)  # TODO Need to add commands with no category here as well >_>
        for cogname in sorted_cogs:
            cog = ctx.bot.get_cog(cogname)
            # Simple kmaps for these conditions, math is dark magic
            if ((not cogname) or cog) and (
                (isuncategory and cogname is None) or (cogname in category.cogs)
            ):
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
            help_for: commands.Command
            await self.format_command_help(ctx, help_for, help_settings=help_settings)

    async def format_category_help(
        self,
        ctx: Context,
        obj: Category,
        help_settings: HelpSettings,
        get_pages: bool = False,
        **kwargs,
    ):
        coms = await self.get_category_help_mapping(
            ctx, obj, help_settings=help_settings, **kwargs
        )
        if not coms:
            return

        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx)
            if description := obj.long_desc or "":
                emb["embed"]["description"] = f"{description[:250]}"

            all_cog_text = ""
            spacer_list = chain(*(i[1].keys() for i in coms))
            spacing = len(max(spacer_list, key=len))
            for cog_name, data in coms:
                cog_text = "\n" + "\n".join(
                    shorten_line(f"`{name:<{spacing}}:`{command.format_shortdoc_for_context(ctx)}")
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
            await ctx.send(_("You need to enable embeds to use the help menu"))

    async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings):
        coms = await self.get_cog_help_mapping(ctx, obj, help_settings=help_settings)
        if not (coms or help_settings.verify_exists):
            return

        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx, obj.format_help_for_context(ctx))

            if coms:
                spacing = len(max(coms.keys(), key=len))
                command_text = "\n".join(
                    shorten_line(f"`{name:<{spacing}}:`{command.format_shortdoc_for_context(ctx)}")
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
            await ctx.send(_("You need to enable embeds to use the help menu"))

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

        signature = _(
            "```yaml\nSyntax: {ctx.clean_prefix}{command.qualified_name} {command.signature}\n```"
        ).format(ctx=ctx, command=command)
        subcommands = None

        if hasattr(command, "all_commands"):
            grp = cast(commands.Group, command)
            subcommands = await self.get_group_help_mapping(ctx, grp, help_settings=help_settings)

        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx)

            if description:
                emb["embed"]["title"] = f"{description[:250]}"

            emb["embed"]["description"] = signature

            command_help = command.format_help_for_context(ctx)
            if command_help:
                splitted = command_help.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                if not value:
                    value = EMPTY_STRING
                field = EmbedField(name[:250], value[:1024], False)
                emb["fields"].append(field)

                if alias := get_aliases(command, ctx.invoked_with):
                    emb["fields"].append(EmbedField("Aliases", ",".join(alias), False))

                if final_perms := get_perms(command):
                    emb["fields"].append(EmbedField("Permissions", final_perms, False))

                if cooldowns := get_cooldowns(command):
                    emb["fields"].append(EmbedField("Cooldowns", "\n".join(cooldowns), False))

            if subcommands:
                spacing = len(max(subcommands.keys(), key=len))
                subtext = "\n" + "\n".join(
                    shorten_line(f"`{name:<{spacing}}:`{command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(subcommands.items())
                )
                for i, page in enumerate(pagify(subtext, page_length=500, shorten_by=0)):
                    if i == 0:
                        title = _("**__Subcommands:__**")
                    else:
                        title = EMPTY_STRING
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)
            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            await self.send_pages(ctx, pages, embed=True, help_settings=help_settings)
        else:
            await ctx.send(_("You need to enable embeds to use the help menu"))

    async def format_bot_help(
        self, ctx: Context, help_settings: HelpSettings, get_pages: bool = False
    ):
        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx, ctx.bot.description)
            filtered_categories = await self.filter_categories(ctx, GLOBAL_CATEGORIES)
            for i in pagify(
                "\n".join(
                    f"{str(cat.reaction) if cat.reaction else ''} `{ctx.clean_prefix}help {cat.name:<10}:`**{cat.desc}**\n"
                    for cat in filtered_categories
                    if cat.cogs
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
                    emoji_mapping=filtered_categories,
                )
        else:
            await ctx.send(_("You need to enable embeds to use the help menu"))

    # util to reduce code dupes
    async def embed_template(self, help_settings, ctx, description=None):
        emb = {
            "embed": {"title": "", "description": ""},
            "footer": {"text": ""},
            "fields": [],
        }
        if description:
            splitted = description.split("\n\n")
            name = splitted[0]
            value = "\n\n".join(splitted[1:])
            if not value:
                value = EMPTY_STRING
            field = EmbedField(name[:250], value[:1024], False)
            emb["fields"].append(field)
        emb["footer"]["text"] = (help_settings.tagline) or self.get_default_tagline(ctx)
        return emb

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
                description = _("Page {page_num} of {page_count}\n{content_description}").format(
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
        emoji_mapping: list = None,
    ):
        """
        Sends pages based on settings.
        """

        # save on config calls
        channel_permissions = ctx.channel.permissions_for(ctx.me)

        if channel_permissions.manage_messages and await self.config.settings.deletemessage():
            await ctx.message.delete()

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
            # m = await (ctx.send(embed=pages[0]) if embed else ctx.send(pages[0]))
            trans = {
                "left": prev_page,
                "cross": close_menu,
                "right": next_page,
            }
            final_menu = get_menu()(ListPages(pages))
            for thing in trans:
                final_menu.add_button(trans[thing](emoji_converter(ctx.bot, ARROWS[thing])))

            if not add_emojis:
                # Add force left and right reactions when emojis are off, cause why not xD
                final_menu.add_button(first_page(emoji_converter(ctx.bot, ARROWS["force_left"])))
                final_menu.add_button(last_page(emoji_converter(ctx.bot, ARROWS["force_right"])))

            # TODO important!
            if add_emojis and emoji_mapping:
                # Adding additional category emojis
                for cat in emoji_mapping:
                    if cat.reaction:
                        final_menu.add_button(
                            await react_page(ctx, cat.reaction, help_settings, bypass_checks=True)
                        )
                final_menu.add_button(
                    await home_page(ctx, emoji_converter(ctx.bot, ARROWS["home"]), help_settings)
                )
            await final_menu.start(ctx)

    async def blacklist(self, ctx, name) -> bool:
        """Some blacklist checks utils
        Returns true if needed to be shown"""
        blocklist = await self.config.blacklist()
        a = (
            ctx.channel.is_nsfw() if hasattr(ctx.channel, "is_nsfw") else True
        ) or name not in blocklist["nsfw"]

        b = await self.bot.is_owner(ctx.author) or name not in blocklist["dev"]
        return a and b

    async def filter_categories(self, ctx, categories: list) -> list:
        """Applies blacklist to all the categories, Filters based on the current context"""
        blocklist = await self.config.blacklist()
        is_owner = await self.bot.is_owner(ctx.author)
        final = []
        for name in categories:
            # This condition is made using a simple kmap.
            if (
                (ctx.channel.is_nsfw() if hasattr(ctx.channel, "is_nsfw") else True)
                or name not in blocklist["nsfw"]
            ) and (is_owner or name not in blocklist["dev"]):
                final.append(name)
        return final
