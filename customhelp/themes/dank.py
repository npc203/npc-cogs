from ..abc import ThemesMeta
from ..core.base_help import (
    EMPTY_STRING,
    GLOBAL_CATEGORIES,
    Category,
    Context,
    EmbedField,
    HelpSettings,
    _,
    cast,
    commands,
    get_aliases,
    get_cooldowns,
    get_perms,
    pagify,
)


class DankHelp(ThemesMeta):
    """Inspired from Dankmemer's help menu"""

    async def format_bot_help(
        self, ctx: Context, help_settings: HelpSettings, get_pages: bool = False
    ):

        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx)
            description = ctx.bot.description or ""
            emb["embed"]["description"] = description

            filtered_categories = await self.filter_categories(ctx, GLOBAL_CATEGORIES)
            # Maybe add category desc with long_desc somewhere?
            for cat in filtered_categories:
                if cat.cogs:
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
                    emoji_mapping=filtered_categories,
                )
        else:
            await ctx.send(_("You need to enable embeds to use the help menu"))

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
            emb["embed"]["title"] = (
                (str(obj.reaction) if obj.reaction else "") + " " + obj.name.capitalize()
            )
            if description := obj.long_desc:
                emb["embed"]["description"] = f"{description[:250]}"

            all_cog_text = [
                ", ".join(f"`{name}`" for name, command in sorted(data.items()))
                for cog_name, data in coms
            ]

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
        signature = _("`{ctx.clean_prefix}{command.qualified_name} {command.signature}`").format(
            ctx=ctx, command=command
        )
        subcommands = None

        if hasattr(command, "all_commands"):
            grp = cast(commands.Group, command)
            subcommands = await self.get_group_help_mapping(ctx, grp, help_settings=help_settings)

        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx)
            if description := command.description:
                emb["embed"]["title"] = f"{description[:250]}"

            command_help = command.format_help_for_context(ctx)
            if command_help:
                splitted = command_help.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                emb["fields"].append(EmbedField("Description:", name[:250], False))
            else:
                value = ""
            emb["fields"].append(EmbedField("Usage:", signature, False))

            if aliases := get_aliases(command, ctx.invoked_with):
                emb["fields"].append(EmbedField("Aliases", ", ".join(aliases), False))

            if final_perms := get_perms(command):
                emb["fields"].append(EmbedField("Permissions", final_perms, False))

            if cooldowns := get_cooldowns(command):
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
            await ctx.send(_("You need to enable embeds to use the help menu"))
