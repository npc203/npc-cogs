import asyncio
import logging
from collections import Counter, namedtuple
from collections.abc import Iterable
from itertools import chain
from typing import Any, Dict, List, Optional, Union, cast

import discord
from redbot.core import commands
from redbot.core.commands.commands import Command
from redbot.core.commands.context import Context
from redbot.core.commands.help import HelpSettings, NoCommand, NoSubCommand, _, dpy_commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.mod import mass_purge

from customhelp.core.views import (
    BaseInteractionMenu,
    ReactButton,
    SelectArrowHelpBar,
    SelectMenuHelpBar,
)

from . import ARROWS, GLOBAL_CATEGORIES
from .category import Category, get_category
from .dpy_menus import BaseMenu, arrow_react, home_react, react_page
from .utils import (
    get_aliases,
    get_category_page_mapper_chunk,
    get_cooldowns,
    get_perms,
    shorten_line,
)

LOG = logging.getLogger("red.customhelp.core.base_help")

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
# page_mapping = { category_obj: generated_category_format_page}
class BaguetteHelp(commands.RedHelpFormatter):
    """In the memory of Jack the virgin"""

    def __init__(self, bot, settings, blacklist):
        self.bot = bot
        self.settings = settings
        self.blacklist_names = blacklist

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
        if category.name == GLOBAL_CATEGORIES.uncategorised.name:
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
        help_for: Optional[HelpTarget] = None,
        *,
        from_help_command: bool = False,
    ):
        """
        Parses the help thing requested fora
        """

        help_settings = await HelpSettings.from_context(ctx)

        if help_for is None or isinstance(help_for, dpy_commands.bot.BotBase):
            await self.format_bot_help(ctx, help_settings=help_settings)
            return

        if isinstance(help_for, str):
            try:
                help_for = await self.parse_command(ctx, help_for)  # type:ignore
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
            emb["thumbnail"] = obj.thumbnail

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
            for page in pagify(all_cog_text, page_length=500, shorten_by=0):
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
        coms: Dict[str, Command] = await self.get_cog_help_mapping(
            ctx, obj, help_settings=help_settings
        )  # type:ignore
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

                for i, page in enumerate(
                    pagify(name + "\n" + value, page_length=1024, shorten_by=0)
                ):
                    if i == 0:
                        title = "Description"
                    else:
                        title = EMPTY_STRING

                    field = EmbedField(title, page, False)
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

            page_raw_str_data = []
            page_mapping = {}
            for cat in filtered_categories:
                if cat.cogs:
                    if not await get_category_page_mapper_chunk(
                        self, get_pages, ctx, cat, help_settings, page_mapping
                    ):
                        continue

                    page_raw_str_data.append(
                        f"{str(cat.reaction) if cat.reaction else ''} `{ctx.clean_prefix}help {cat.name:<10}:`**{cat.desc}**\n"
                    )

            for i in pagify("\n".join(page_raw_str_data), page_length=1018):
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
                    page_mapping=page_mapping,
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
        thumbnail_url = embed_dict.get("thumbnail", None) or self.settings["thumbnail"]
        page_char_limit = help_settings.page_char_limit
        page_char_limit = min(page_char_limit, 5500)
        author_info = {
            "name": _("{ctx.me.display_name} Help Menu").format(ctx=ctx),
            "icon_url": ctx.me.display_avatar.url,
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
        page_mapping: Dict[Category, List] = {},
        *,
        help_settings: HelpSettings,
    ):
        """
        Sends pages based on settings.
        If page_mapping is non-empty, then it's the main help menu and we need to add the home button
        """

        # save on config calls
        channel_permissions = ctx.channel.permissions_for(ctx.me)

        if channel_permissions.manage_messages and self.settings["deletemessage"]:
            await ctx.message.delete()

        if not (channel_permissions.add_reactions and help_settings.use_menus):
            max_pages_in_guild = help_settings.max_pages_in_guild
            use_DMs = len(pages) > max_pages_in_guild
            destination = ctx.author if use_DMs else ctx.channel
            delete_delay = help_settings.delete_delay
            messages: List[discord.Message] = []
            for page in pages:
                # TODO use the embed:bool on the function argument cause isinstance is costly
                page_kwarg_dict = (
                    {"embed": page} if isinstance(page, discord.Embed) else {"content": page}
                )
                try:
                    msg = await destination.send(**page_kwarg_dict)
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
                    channel,
                    messages: List[discord.Message],
                    delay: int,
                ):
                    await asyncio.sleep(delay)
                    await mass_purge(messages, channel)

                asyncio.create_task(_delete_delay_help(destination, messages, delete_delay))
        else:
            menu = HybridMenus(self.settings, help_settings, page_mapping, pages)
            await menu.start(ctx)

    async def blacklist(self, ctx, name) -> bool:
        """Some blacklist checks utils
        Returns true if needed to be shown"""
        blocklist = self.blacklist_names
        a = (
            ctx.channel.is_nsfw() if hasattr(ctx.channel, "is_nsfw") else True
        ) or name not in blocklist["nsfw"]

        b = await self.bot.is_owner(ctx.author) or name not in blocklist["dev"]
        return a and b

    async def filter_categories(self, ctx, categories: Iterable) -> list:
        """Applies blacklist to all the categories, Filters based on the current context"""
        blocklist = self.blacklist_names
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


class HybridMenus:
    def __init__(self, settings, helpsettings, page_mapping: Dict[Category, List], pages):
        self.arrow_emoji_button = {
            "force_left": self.first_page,
            "left": self.prev_page,
            "cross": self.close_menu,
            "right": self.next_page,
            "force_right": self.last_page,
        }

        self.settings = settings
        self.help_settings = helpsettings
        self.menus: List[Any] = [None, None]  # dpy menus, views

        # Source specific
        self.curr_page = 0
        self.pages: List[Union[str, discord.Embed]] = pages
        self.category_page_mapping = page_mapping
        self.no_arrows_yet = False

    async def get_pages(self, ctx: commands.Context, category_name: str):
        if not (category_pages := self.category_page_mapping.get(category_name)):
            if category_name.lower() == "home":
                category_pages = await ctx.bot._help_formatter.format_bot_help(
                    ctx, self.help_settings, get_pages=True
                )
            self.category_page_mapping[category_name] = category_pages

        return category_pages

    def change_source(self, new_source):
        self.pages = new_source
        self.curr_page = 0

    async def show_current_page(self, interaction, **kwargs):
        data = self._get_kwargs_from_page(self.pages[self.curr_page])
        if isinstance(interaction, discord.Message):
            await interaction.edit(**data, **kwargs)
        else:
            await interaction.response.edit_message(**data, **kwargs)

    async def start(self, ctx):
        await self.create_menutype()
        await self.create_arrowtype(ctx)
        # Start dpy2 menus (and then views if they exist) else start just the views
        if self.menus[0]:
            message = await self.menus[0].start(ctx)
            if self.menus[1]:
                await self.menus[1].start(ctx, message=message)
            self.bot_message = message
        elif self.menus[1]:
            await self.menus[1].start(ctx)
            self.bot_message = self.menus[1].message

    def _get_kwargs_from_page(self, value):
        kwargs: dict[str, Any] = {"allowed_mentions": discord.AllowedMentions(replied_user=False)}
        if isinstance(value, dict):
            kwargs.update(value)
        elif isinstance(value, str):
            kwargs["content"] = value
        elif isinstance(value, discord.Embed):
            kwargs["embed"] = value
        return kwargs

    async def create_menutype(self):
        """MenuType component"""
        # We are not at the homepage
        if not self.category_page_mapping:
            return

        # TODO use match-case on 3.10
        if self.settings["menutype"] == "emojis":
            dpy_menu = BaseMenu(hmenu=self)
            # Category buttons
            for cat, pages in self.category_page_mapping.items():
                if cat.reaction:
                    dpy_menu.add_button(await react_page(cat, pages))
            self.menus[0] = dpy_menu
        elif self.settings["menutype"] != "hidden":
            view_menu = BaseInteractionMenu(hmenu=self)
            if self.settings["menutype"] == "buttons":
                # Category buttons
                for cat, pages in self.category_page_mapping.items():
                    if cat.reaction or cat.label:
                        view_menu.add_item(
                            ReactButton(
                                emoji=cat.reaction,
                                style=getattr(discord.ButtonStyle, cat.style),
                                label=cat.label,
                                custom_id=cat.name,
                            )
                        )
            else:  # Select
                options = []
                # Category buttons
                for cat in self.category_page_mapping:
                    # Kinda hacky
                    if cat.desc == "Not provided":
                        category_desc = None
                    else:
                        category_desc = cat.desc

                    options.append(
                        discord.SelectOption(
                            label=cat.name,
                            description=category_desc,
                            emoji=cat.reaction,
                        )
                    )

                select_bar = SelectMenuHelpBar(options)
                view_menu.add_item(select_bar)

            self.menus[1] = view_menu

    async def create_arrowtype(self, ctx):
        """ArrowType component"""
        if self.settings["arrowtype"] == "emojis":
            if not self.menus[0]:
                dpy_menu = BaseMenu(hmenu=self)
                self.menus[0] = dpy_menu
            else:
                dpy_menu = self.menus[0]

            if len(self.pages) == 1:
                self.no_arrows_yet = True
                dpy_menu.add_button(await arrow_react(ARROWS["cross"]))
            else:
                for arrow in ARROWS:
                    if arrow.name == "home":
                        # Main page alone shows the home button
                        if self.category_page_mapping:
                            dpy_menu.add_button(await home_react(arrow.emoji))
                        continue
                    if self.settings["nav"]:  # Fix this later, crap inefficient code
                        dpy_menu.add_button(await arrow_react(arrow))

        elif self.settings["arrowtype"] != "hidden":
            if not self.menus[1]:
                self.menus[1] = BaseInteractionMenu(hmenu=self)
            view_menu = self.menus[1]

            if self.settings["arrowtype"] == "buttons":
                # Main page alone shows the home button
                if self.category_page_mapping:
                    # haccerman
                    home_style = Counter([arrow.style for arrow in ARROWS]).most_common(1)[0][0]
                    # If menutype is select, chug it in the select bar
                    # To save space
                    if self.settings["menutype"] == "select":
                        for child in view_menu.children:
                            if type(child) == SelectMenuHelpBar:
                                child.add_option(
                                    label="Home",
                                    description="Go to the main page",
                                    emoji=ARROWS["home"].emoji,
                                )
                                break
                    else:
                        view_menu.add_item(
                            ReactButton(
                                emoji=ARROWS["home"].emoji,
                                style=home_style,
                                custom_id="home",
                                row=3 if self.settings["menutype"] != "buttons" else None,
                            )
                        )

                class Button(discord.ui.Button):
                    view: BaseInteractionMenu

                    def __init__(self, name, row=4, **kwargs):
                        self.name = name
                        super().__init__(**kwargs, row=row)

                    async def callback(self, interaction):
                        await self.view.hmenu.arrow_emoji_button[self.name](interaction)

                if self.settings["nav"]:
                    if len(self.pages) == 1:
                        self.no_arrows_yet = True
                        arrow = ARROWS["cross"]
                        button = Button(arrow.name, **arrow.items(), row=None)
                        view_menu.add_item(button)
                    else:
                        for arrow in ARROWS:
                            if arrow.name == "home":
                                continue
                            # TODO remove subclass later (dont need a state for each button)
                            button = Button(arrow.name, **arrow.items())
                            view_menu.add_item(button)

            else:  # Select
                options = []
                if self.settings["nav"]:
                    for arrow in ARROWS:
                        if arrow.name == "home":
                            continue
                        options.append(
                            discord.SelectOption(
                                label=arrow.name,
                                emoji=arrow.emoji,
                            )
                        )
                # Main page alone shows the home button
                if self.category_page_mapping:
                    options.append(
                        discord.SelectOption(
                            label="Home",
                            description="Return to the main page",
                            emoji=ARROWS["home"].emoji,
                        )
                    )
                select_bar = SelectArrowHelpBar(options)
                view_menu.add_item(select_bar)

    def stop(self):
        for menu in self.menus:
            if menu:
                menu.stop()

    # MENU ACTIONS BLOCK #
    async def category_react_action(
        self, user_ctx: commands.Context, interaction, category_name: str
    ):
        if category_pages := await self.get_pages(user_ctx, category_name):
            self.change_source(category_pages)

            # Dynamically pull up arrows if we have more than one page
            # And we maintain the arrows, even if we go back to pages of size 1
            if self.no_arrows_yet and len(self.pages) > 1:
                if self.settings["arrowtype"] == "emojis":
                    # Copy Pasta from create_arrowtype
                    for arrow in ARROWS:
                        if arrow.name == "home":
                            # We already must have come from the home page
                            # else we wouldn't have the category buttons
                            continue
                        if arrow.name == "cross":
                            # home page already has cross
                            continue
                        if self.settings["nav"]:
                            await self.menus[0].add_button(await arrow_react(arrow), react=True)

                if self.settings["arrowtype"] == "buttons":
                    # Buttons/select
                    # We recreate the menu, so we can add the arrows
                    sender_ctx = self.menus[1].ctx
                    bot_message = self.menus[1].message

                    # This is needed for the interaction to not failed,
                    # when the category is a button
                    if type(interaction) == discord.Interaction:
                        await interaction.response.defer()

                    self.menus[1].clear_items()

                    await self.create_menutype()
                    await self.create_arrowtype(sender_ctx)
                    await self.menus[1].start(ctx=sender_ctx, message=bot_message)

                if any(self.menus):
                    await self.show_current_page(self.bot_message, view=self.menus[1])

                self.no_arrows_yet = False
            else:
                await self.show_current_page(interaction)

    async def home_page(self, ctx, interaction):
        self.change_source(await self.get_pages(ctx, "home"))
        await self.show_current_page(interaction)

    async def first_page(self, interaction):
        self.curr_page = 0
        await self.show_current_page(interaction)

    async def last_page(self, interaction):
        self.curr_page = len(self.pages) - 1
        await self.show_current_page(interaction)

    async def next_page(self, interaction):
        if self.curr_page < len(self.pages) - 1:
            self.curr_page += 1
            await self.show_current_page(interaction)
        else:
            await self.first_page(interaction)

    async def prev_page(self, interaction):
        if self.curr_page > 0:
            self.curr_page -= 1
            await self.show_current_page(interaction)
        else:
            await self.last_page(interaction)

    async def close_menu(self, interaction):
        self.stop()
        await self.bot_message.delete()
