from ..abc import ThemesMeta
from ..core.base_help import (
    GLOBAL_CATEGORIES,
    Category,
    Context,
    HelpSettings,
    _,
    cast,
    chain,
    commands,
    get_aliases,
    get_cooldowns,
    get_perms,
    pagify,
)


class MinimalHelp(ThemesMeta):
    """This is a no embed minimal theme for the simplistic people.\nThis won't use reactions.\nThanks OwO for design advices"""

    async def format_bot_help(
        self,
        ctx: Context,
        help_settings: HelpSettings,
        get_pages: bool = False,
    ):
        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        full_text = f"{description}\n\n{tagline}"

        filtered_categories = await self.filter_categories(ctx, GLOBAL_CATEGORIES)
        # Maybe add category desc somewhere?
        for cat in filtered_categories:
            if cat.cogs:
                coms = await self.get_category_help_mapping(ctx, cat, help_settings=help_settings)
                all_cog_text = [" · ".join(f"{name}" for name in data) for cogname, data in coms]
                all_cog_text = " · ".join(all_cog_text)
                full_text += f"\n\n__**{cat.name}**__: {all_cog_text}"
        text_no = list(pagify(full_text))
        if get_pages:
            return text_no
        await self.send_pages(
            ctx,
            text_no,
            embed=False,
            help_settings=help_settings,
            emoji_mapping=filtered_categories,
        )

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

        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        full_text = f"{description}\n\n{tagline}\n\n"

        spacer_list = chain(*(i[1].keys() for i in coms))
        spacing = len(max(spacer_list, key=len))
        for cogname, data in coms:
            full_text += "\n".join(
                f"`{name:<{spacing}}`:{command.format_shortdoc_for_context(ctx)}"
                for name, command in data.items()
            )
            full_text += "\n"
        text_no = list(pagify(full_text))
        if get_pages:
            return text_no
        await self.send_pages(
            ctx,
            text_no,
            embed=False,
            help_settings=help_settings,
        )

    async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings):
        coms = await self.get_cog_help_mapping(ctx, obj, help_settings=help_settings)
        if not (coms or help_settings.verify_exists):
            return
        description = obj.format_help_for_context(ctx) or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        full_text = f"{description}\n\n{tagline}\n\n"

        spacing = len(max(coms.keys(), key=len))
        full_text += "\n".join(
            f"`{name:<{spacing}}:`{command.format_shortdoc_for_context(ctx)}"
            for name, command in sorted(coms.items())
        )
        pages = list(pagify(full_text))
        await self.send_pages(ctx, pages, embed=False, help_settings=help_settings)

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

        signature = _("`{ctx.clean_prefix}{command.qualified_name} {command.signature}`").format(
            ctx=ctx, command=command
        )
        subcommands = None

        if hasattr(command, "all_commands"):
            grp = cast(commands.Group, command)
            subcommands = await self.get_group_help_mapping(ctx, grp, help_settings=help_settings)

        full_text = ""
        command_help = command.format_help_for_context(ctx)
        if command_help:
            splitted = command_help.split("\n\n")
            name = splitted[0]
            value = "\n".join(splitted[1:])
        full_text += "**Usage:** `" + signature + "`\n"

        if aliases := get_aliases(command, ctx.invoked_with):
            full_text += "**Aliases:** " + ",".join(aliases) + "\n"

        if cooldowns := get_cooldowns(command):
            full_text += "**Cooldowns:** " + "\n".join(cooldowns) + "\n"

        if final_perms := get_perms(command):
            full_text += "**Permissions:**\n" + final_perms + "\n"

        if command_help:
            full_text += (
                "**Description:**\n" + name + "\n" + (value + "\n" if value else "") + "\n"
            )

        if subcommands:
            spacing = len(max(subcommands.keys(), key=len))
            subtext = "\n" + "\n".join(
                f"`{name:<{spacing}}`:{command.format_shortdoc_for_context(ctx)}"
                for name, command in sorted(subcommands.items())
            )
            for i, page in enumerate(pagify(subtext, shorten_by=0)):
                if i == 0:
                    title = _("**__Subcommands:__**")
                else:
                    title = ""
                full_text += f"{title}{page}"
        text_no = list(pagify(full_text))
        await self.send_pages(
            ctx,
            text_no,
            embed=False,
            help_settings=help_settings,
        )
