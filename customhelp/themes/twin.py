from ..abc import ThemesMeta
from ..core.base_help import (
    EMPTY_STRING,
    GLOBAL_CATEGORIES,
    Category,
    Context,
    EmbedField,
    HelpSettings,
    _,
    get_category_page_mapper_chunk,
    pagify,
)


class TwinHelp(ThemesMeta):
    """This help is designed by TwinShadow a.k.a TwinShadow#0666"""

    async def format_bot_help(
        self, ctx: Context, help_settings: HelpSettings, get_pages: bool = False
    ):
        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx, ctx.bot.description)
            filtered_categories = await self.filter_categories(ctx, GLOBAL_CATEGORIES)
            page_mapping = {}
            for cat in filtered_categories:
                if cat.cogs:
                    if not await get_category_page_mapper_chunk(
                        self, get_pages, ctx, cat, help_settings, page_mapping
                    ):
                        continue
                    cog_names = "`" + "` `".join(cat.cogs) + "`" if cat.cogs else ""
                    for i, page in enumerate(pagify(cog_names, page_length=1000, shorten_by=0)):
                        if i == 0:
                            title = (
                                cat.reaction and str(cat.reaction) or ""
                            ) + f"  __{cat.name.capitalize()}:__ "
                        else:
                            title = EMPTY_STRING
                        emb["fields"].append(EmbedField(title, cog_names, False))
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
            emb = await self.embed_template(help_settings, ctx, obj.long_desc)

            for cog_name, data in coms:
                title = f"__**{cog_name}**__" if cog_name else _("**No Category:**")
                cog_text = ", ".join(f"`{name}`" for name, command in sorted(data.items()))
                for i, page in enumerate(
                    pagify(cog_text, page_length=1000, delims=[","], shorten_by=0)
                ):
                    if i > 0:
                        title = f"**{cog_name} (continued):**"
                    field = EmbedField(
                        title, page[1:] if page.startswith(",") else page, False
                    )  # precision matters xd
                    emb["fields"].append(field)

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            if get_pages:
                return pages
            else:
                await self.send_pages(ctx, pages, embed=True, help_settings=help_settings)
        else:
            await ctx.send(_("You need to enable embeds to use the help menu"))
