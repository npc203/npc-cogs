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
)


class TwinHelp:
    """This help is made by TwinShadow a.k.a TwinShadow#0666"""

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
                splitted = description.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                if not value:
                    value = EMPTY_STRING
                field = EmbedField(name[:252], value[:1024], False)
                emb["fields"].append(field)

            for cog_name, data in coms:
                if cog_name:
                    title = f"**{cog_name}**"
                else:
                    title = _("**No Category:**")
                cog_text = ", ".join(
                    f"`{name}`" for name, command in sorted(data.items())
                )
                for i, page in enumerate(
                    pagify(cog_text, page_length=1000, shorten_by=0)
                ):
                    field = EmbedField(title, page, False)
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
