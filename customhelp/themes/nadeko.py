from redbot.core.utils.chat_formatting import box

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


class NadekoHelp(ThemesMeta):
    """Inspired from Nadeko's help menu"""

    async def format_bot_help(
        self, ctx: Context, help_settings: HelpSettings, get_pages: bool = False
    ):
        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx, ctx.bot.description)
            filtered_categories = await self.filter_categories(ctx, GLOBAL_CATEGORIES)
            page_mapping = {}
            cat_titles = ""
            for cat in filtered_categories:
                if cat.cogs:
                    if not await get_category_page_mapper_chunk(
                        self, get_pages, ctx, cat, help_settings, page_mapping
                    ):
                        continue
                    cat_titles += f"• {cat.name}\n"

            # TODO Dont be a moron trying to pagify this or do we? yes we do, lmao.
            for i, vals in enumerate(pagify(cat_titles, page_length=1000)):
                emb["fields"].append(
                    EmbedField(
                        (_("List of Categories") if i < 1 else EMPTY_STRING + " "), vals, False
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
            emb = await self.embed_template(help_settings, ctx)
            if description := obj.long_desc:
                emb["embed"]["description"] = f"{description[:250]}"

            for cog_name, data in coms:
                title = f"**{cog_name}**" if cog_name else _("**No Category:**")
                cog_text = [
                    f"{ctx.clean_prefix}{name:<15}{command.aliases}"
                    for name, command in sorted(data.items())
                ]
                # need to customize this
                for i, page in enumerate(
                    (cog_text[n : n + 7] for n in range(0, len(cog_text), 7))
                ):
                    field = EmbedField(
                        title if i < 1 else _("{title} (continued)").format(title=title),
                        box("\n".join(page), lang="css"),
                        True,
                    )
                    emb["fields"].append(field)

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            if get_pages:
                return pages
            else:
                await self.send_pages(ctx, pages, embed=True, help_settings=help_settings)
        else:
            await ctx.send(_("You need to enable embeds to use the help menu"))
