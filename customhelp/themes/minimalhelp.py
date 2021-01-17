from ..core.base_help import (
    BaguetteHelp,
    pagify,
    EmbedField,
    EMPTY_STRING,
    Context,
    CategoryConvert,
    HelpSettings,
    _,
    discord,
    commands,
    box,
    GLOBAL_CATEGORIES,
    cast,
    humanize_timedelta,
)

# Note: this won't use reactions
class MinimalHelp:
    async def format_bot_help(self, ctx: Context, help_settings: HelpSettings):
        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        full_text = f"{description}\n\n{tagline}"
        # Maybe add category desc somewhere?
        for cat in GLOBAL_CATEGORIES:
            coms = await self.get_category_help_mapping(
                ctx, cat, help_settings=help_settings
            )
            all_cog_text = ""
            for _, data in coms:
                all_cog_text += " · ".join(f"{name}" for name in data) + " · "

            full_text += f"\n\n__**{cat.name}**__: {all_cog_text}"
        text_no = list(pagify(full_text))
        if len(text_no) > 1:
            pages = [
                page + f"\n\nPage:{i}/{len(text_no)}"
                for i, page in enumerate(text_no, 1)
            ]
        else:
            pages = [page for i, page in enumerate(text_no, 1)]
        await self.send_pages(
            ctx,
            pages,
            embed=False,
            help_settings=help_settings,
        )

    async def format_category_help(
        self, ctx: Context, obj: CategoryConvert, help_settings: HelpSettings
    ):
        coms = await self.get_category_help_mapping(
            ctx, obj, help_settings=help_settings
        )
        if not coms:
            return

        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        full_text = f"{description}\n\n{tagline}\n\n"
        for _, data in coms:
            full_text += "\n".join(
                f"**{name}**–{command.format_shortdoc_for_context(ctx)}"
                for name, command in data.items()
            )
            full_text += "\n"
        text_no = list(pagify(full_text))
        if len(text_no) > 1:
            pages = [
                page + f"\n\nPage:{i}/{len(text_no)}"
                for i, page in enumerate(text_no, 1)
            ]
        else:
            pages = [page for i, page in enumerate(text_no, 1)]
        await self.send_pages(
            ctx,
            pages,
            embed=False,
            help_settings=help_settings,
        )

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
            "`{ctx.clean_prefix}{command.qualified_name} {command.signature}`"
        ).format(ctx=ctx, command=command)
        aliases = command.aliases
        subcommands = None

        if hasattr(command, "all_commands"):
            grp = cast(commands.Group, command)
            subcommands = await self.get_group_help_mapping(
                ctx, grp, help_settings=help_settings
            )

        # full_text = f"{description}\n\n{tagline}\n\n"
        full_text = ""
        command_help = command.format_help_for_context(ctx)
        if command_help:
            splitted = command_help.split("\n\n")
            name = splitted[0]
            value = "\n\n".join(splitted[1:])
            full_text += "**Usage:**\n" + signature + "\n\n"
            full_text += "**" + name[:250] + "\n" + value[:1024] + "**\n"
            if aliases:
                full_text = "**Aliases:**\n" + (",".join(aliases)) + "\n"
            # Add permissions
            if perms := command.requires.user_perms:
                perms_list = [
                    i for i, j in perms if j
                ]  # TODO pls learn more to fix this
                if perms_list:
                    full_text += "**Permissions:**\n" + ",".join(perms_list) + "\n"

            # Add cooldowns
            if s := command._buckets._cooldown:
                full_text += (
                    "**Cooldowns:**\n"
                    + f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)} per {s.type.__str__().replace('BucketType.','').capitalize()}"
                )

        if subcommands:
            subtext = "\n" + "\n".join(
                f"**{name}**–{command.format_shortdoc_for_context(ctx)}"
                for name, command in sorted(subcommands.items())
            )
            for i, page in enumerate(pagify(subtext, shorten_by=0)):
                if i == 0:
                    title = _("**__Subcommands:__**")
                else:
                    title = _(EMPTY_STRING)
                full_text += f"{title}{page}"
        text_no = list(pagify(full_text))
        if len(text_no) > 1:
            pages = [
                page + f"\n\nPage:{i}/{len(text_no)}"
                for i, page in enumerate(text_no, 1)
            ]
        else:
            pages = [page for i, page in enumerate(text_no, 1)]
        await self.send_pages(
            ctx,
            pages,
            embed=False,
            help_settings=help_settings,
        )
