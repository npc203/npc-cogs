from ..abc import ThemesMeta
from ..core.base_help import (
    EMPTY_STRING, GLOBAL_CATEGORIES, CategoryConvert, Context, EmbedField,
    HelpSettings, _, cast, commands, humanize_timedelta, pagify)


class DankHelp(ThemesMeta):
    """Inspired from Dankmemer's help menu"""

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
            emb["embed"]["description"] = description
            emb["title"] = f"{ctx.me.name} Help Menu"
            # Maybe add category desc somewhere?
            for cat in GLOBAL_CATEGORIES:
                if cat.cogs and await self.blacklist(ctx, cat.name):
                    title = (
                        str(cat.reaction) + " " if cat.reaction else ""
                    ) + cat.name.capitalize()
                    emb["fields"].append(
                        EmbedField(
                            title,
                            f"`{ctx.clean_prefix}help {cat.name}`\n{cat.long_desc if cat.long_desc else ''}",
                            True,
                        )
                    )
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

            emb["embed"]["title"] = (
                (str(obj.reaction) if obj.reaction else "") + " " + obj.name.capitalize()
            )
            emb["footer"]["text"] = tagline
            if description:
                emb["embed"]["description"] = f"*{description[:250]}*"

            all_cog_text = []
            for cog_name, data in coms:
                all_cog_text.append(
                    ", ".join(f"`{name}`" for name, command in sorted(data.items()))
                )
            all_cog_text = ", ".join(all_cog_text)
            for i, page in enumerate(
                pagify(all_cog_text, page_length=1000, delims=[","], shorten_by=0)
            ):
                field = EmbedField(
                    EMPTY_STRING,
                    page[1:] if page.startswith(",") else page,
                    False,
                )
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
            await ctx.send("Enable embeds please")

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
        signature = _("`{ctx.clean_prefix}{command.qualified_name} {command.signature}`").format(
            ctx=ctx, command=command
        )
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
            # emb["embed"]["description"] = signature

            command_help = command.format_help_for_context(ctx)
            if command_help:
                splitted = command_help.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                emb["fields"].append(EmbedField("Description:", name[:250], False))
            else:
                value = ""
            emb["fields"].append(EmbedField("Usage:", signature, False))

            # Add aliases
            if alias := command.aliases:
                if ctx.invoked_with in alias:
                    alias.remove(ctx.invoked_with)
                    alias.append(command.name)
                emb["fields"].append(EmbedField("Aliases", ", ".join(alias), False))

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
                emb["fields"].append(EmbedField("Permissions", ", ".join(final_perms), False))
            # Add cooldowns
            cooldowns = []
            if s := command._buckets._cooldown:
                cooldowns.append(
                    f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)} per {s.type.name.capitalize()}"
                )
            if s := command._max_concurrency:
                cooldowns.append(f"Max concurrent uses: {s.number} per {s.per.name.capitalize()}")
            if cooldowns:
                emb["fields"].append(EmbedField("Cooldowns:", "\n".join(cooldowns), False))
            if value:
                emb["fields"].append(EmbedField("Full description:", value[:1024], False))

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
            await self.send_pages(
                ctx,
                pages,
                embed=True,
                help_settings=help_settings,
            )
        else:
            await ctx.send("Enable embeds pls")
