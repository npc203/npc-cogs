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
    cast,
    GLOBAL_CATEGORIES,
)


class JustCore:
    """This is the raw core help, but with categories"""

    async def format_category_help(
        self,
        ctx: Context,
        obj: CategoryConvert,
        help_settings: HelpSettings,
        get_pages: bool = False,
    ):
        coms = await self.get_category_help_mapping(
            ctx, obj, help_settings=help_settings
        )
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
                emb["embed"]["title"] = f"*{description[:250]}*"

            for cog_name, data in coms:
                title = f"**__{cog_name}:__**"

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67] + "..."

                cog_text = "\n".join(
                    shorten_line(
                        f"**{name}** {command.format_shortdoc_for_context(ctx)}"
                    )
                    for name, command in sorted(data.items())
                )

                for i, page in enumerate(
                    pagify(cog_text, page_length=1000, shorten_by=0)
                ):
                    title = (
                        title if i < 1 else _("{title} (continued)").format(title=title)
                    )
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            if get_pages:
                return pages
            else:
                await self.send_pages(
                    ctx,
                    pages,
                    embed=True,
                    help_settings=help_settings,
                )

        else:
            await ctx.send("Please have embeds enabled")

    async def format_command_help(
        self, ctx: Context, obj: commands.Command, help_settings: HelpSettings
    ):

        send = help_settings.verify_exists
        if not send:
            async for __ in self.help_filter_func(
                ctx, (obj,), bypass_hidden=True, help_settings=help_settings
            ):
                # This is a really lazy option for not
                # creating a separate single case version.
                # It is efficient though
                #
                # We do still want to bypass the hidden requirement on
                # a specific command explicitly invoked here.
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
            subcommands = await self.get_group_help_mapping(
                ctx, grp, help_settings=help_settings
            )

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
                field = EmbedField(name[:250], value[:1024], False)
                emb["fields"].append(field)

            if subcommands:

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67] + "..."

                subtext = "\n".join(
                    shorten_line(
                        f"**{name}** {command.format_shortdoc_for_context(ctx)}"
                    )
                    for name, command in sorted(subcommands.items())
                )
                for i, page in enumerate(
                    pagify(subtext, page_length=500, shorten_by=0)
                ):
                    if i == 0:
                        title = _("**__Subcommands:__**")
                    else:
                        title = _("**__Subcommands:__** (continued)")
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            await self.send_pages(
                ctx,
                pages,
                embed=True,
                help_settings=help_settings,
                add_emojis=((await self.config.settings())["react"]) and True,
            )

    async def format_cog_help(
        self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings
    ):

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
                field = EmbedField(name[:252], value[:1024], False)
                emb["fields"].append(field)
            if coms:

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67] + "..."

                command_text = "\n".join(
                    shorten_line(
                        f"**{name}** {command.format_shortdoc_for_context(ctx)}"
                    )
                    for name, command in sorted(coms.items())
                )
                for i, page in enumerate(
                    pagify(command_text, page_length=500, shorten_by=0)
                ):
                    if i == 0:
                        title = _("**__Commands:__**")
                    else:
                        title = _("**__Commands:__** (continued)")
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)
                pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
                await self.send_pages(
                    ctx,
                    pages,
                    embed=True,
                    help_settings=help_settings,
                )
        else:
            await ctx.send(f"Enable embeds please")