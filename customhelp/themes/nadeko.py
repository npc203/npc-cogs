from ..core.base_help import (EMPTY_STRING, GLOBAL_CATEGORIES, BaguetteHelp,
                              CategoryConvert, Context, EmbedField,
                              HelpSettings, _, box, commands, discord, pagify)


class NadekoHelp:
    """Inspired from Nadeko's help menu"""

    async def format_bot_help(
        self, ctx: Context, help_settings: HelpSettings, get_pages: bool = False
    ):
        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        if (
            not await ctx.embed_requested()
        ):  # Maybe redirect to non-embed minimal format
            await ctx.send("You need to enable embeds to use custom help menu")
        else:
            emb = {
                "embed": {"title": "", "description": ""},
                "footer": {"text": ""},
                "fields": [],
            }

            emb["footer"]["text"] = tagline

            emb["title"] = f"{ctx.me.name} Help Menu"
            cat_titles = ""
            for cat in GLOBAL_CATEGORIES:
                cat_titles += f"• {cat.name}\n"
            # TODO Dont be a moron trying to pagify this or do we?
            emb["fields"].append(EmbedField("List of Categories", cat_titles, False))
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
                emb["embed"]["description"] = f"*{description[:250]}*"

            for cog_name, data in coms:
                if cog_name:
                    title = f"**{cog_name}**"
                else:
                    title = _("**No Category:**")
                cog_text = "\n".join(
                    f"{ctx.clean_prefix}{name} {'['+command.signature+']'}"
                    for name, command in sorted(data.items())
                )
                for i, page in enumerate(
                    pagify(cog_text, page_length=1000, shorten_by=0)
                ):
                    title = (
                        title if i < 1 else _("{title} (continued)").format(title=title)
                    )
                    field = EmbedField(title, box(page, lang="ini"), True)
                    emb["fields"].append(field)

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            if get_pages:
                return pages
            else:
                await self.send_pages(
                    ctx, pages, embed=True, help_settings=help_settings
                )
        else:
            # fix this
            await ctx.send("Kindly enable embeds")
