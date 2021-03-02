from ..abc import ThemesMeta
from ..core.base_help import (GLOBAL_CATEGORIES, CategoryConvert, Context,
                              HelpSettings, _, cast, chain, commands,
                              humanize_timedelta, pagify)


class MinimalHelp(ThemesMeta):
    """This is a no embed minimal theme for the simplistic people.\nThis won't use reactions.\nThanks OwO for design advices"""

    async def format_bot_help(self, ctx: Context, help_settings: HelpSettings):
        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        full_text = f"{description}\n\n{tagline}"
        # Maybe add category desc somewhere?
        for cat in GLOBAL_CATEGORIES:
            if cat.cogs and await self.blacklist(ctx, cat.name):
                coms = await self.get_category_help_mapping(ctx, cat, help_settings=help_settings)
                all_cog_text = []
                for _, data in coms:
                    all_cog_text.append(" · ".join(f"{name}" for name in data))
                all_cog_text = " · ".join(all_cog_text)
                full_text += f"\n\n__**{cat.name}**__: {all_cog_text}"
        text_no = list(pagify(full_text))
        await self.send_pages(
            ctx,
            text_no,
            embed=False,
            help_settings=help_settings,
        )

    async def format_category_help(
        self, ctx: Context, obj: CategoryConvert, help_settings: HelpSettings
    ):
        coms = await self.get_category_help_mapping(ctx, obj, help_settings=help_settings)
        if not coms:
            return

        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        full_text = f"{description}\n\n{tagline}\n\n"

        spacer_list = chain(*(i[1].keys() for i in coms))
        spacing = len(max(spacer_list, key=len))
        for _, data in coms:
            full_text += "\n".join(
                f"`{name:<{spacing}}`:{command.format_shortdoc_for_context(ctx)}"
                for name, command in data.items()
            )
            full_text += "\n"
        text_no = list(pagify(full_text))
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
        description = ctx.bot.description or ""
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
        full_text += "**Usage:**\n" + signature + "\n\n"
        if command_help:
            full_text += name[:250] + "\n" + value[:1024] + "\n"

            # Add aliases
            if alias := command.aliases:
                if ctx.invoked_with in alias:
                    alias.remove(ctx.invoked_with)
                    alias.append(command.name)
                full_text += "**Aliases:** " + ",".join(alias) + "\n\n"

        # Add permissions
        get_list = ["user_perms", "bot_perms"]
        final_perms = []
        neat_format = lambda x: " ".join(i.capitalize() for i in x.replace("_", " ").split())
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
            full_text += (
                ("\n" if full_text[-2:] != "\n\n" else "")
                + "**Permissions:** "
                + ", ".join(final_perms)
                + "\n"
            )

        # Add cooldowns
        cooldowns = []
        if s := command._buckets._cooldown:
            cooldowns.append(
                f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)} per {s.type.name.capitalize()}"
            )
        if s := command._max_concurrency:
            cooldowns.append(f"Max concurrent uses: {s.number} per {s.per.name.capitalize()}")
        if cooldowns:
            full_text += (
                ("\n" if full_text[-2:] != "\n\n" else "")
                + "**Cooldowns:**\n"
                + "\n".join(cooldowns)
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
