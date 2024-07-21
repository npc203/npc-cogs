from ..abc import ThemesMeta
from ..core.base_help import (
    EMPTY_STRING,
    GLOBAL_CATEGORIES,
    Category,
    Context,
    EmbedField,
    HelpSettings,
    _,
    chain,
    commands,
    get_category_page_mapper_chunk,
    pagify,
    shorten_line,
)


class Mixture(ThemesMeta):
    """This is a mixture of other themes, a variant filling the lacking features of others"""

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
                    coms = await self.get_category_help_mapping(
                        ctx, cat, help_settings=help_settings
                    )
                    commands_list = ", ".join(
                        ", ".join(f"{name}" for name in data) for _, data in coms
                    )
                    for i, page in enumerate(
                        pagify(commands_list, page_length=1000, delims=[","], shorten_by=0)
                    ):
                        if i == 0:
                            title = (
                                f"{cat.reaction} " if cat.reaction else ""
                            ) + f"**{cat.name.capitalize()}:**"
                        else:
                            title = EMPTY_STRING
                        emb["fields"].append(EmbedField(title, "> " + page, False))
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

            spacer_list = chain(*(i[1].keys() for i in coms))
            spacing = len(max(spacer_list, key=len))

            for cog_name, data in coms:
                title = f"**__{cog_name}:__**"

                cog_text = "\n" + "\n".join(
                    shorten_line(f"`{name:<{spacing}}:`{command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(data.items())
                )
                for i, page in enumerate(pagify(cog_text, page_length=1000, shorten_by=0)):
                    title = title if i < 1 else _("{title} (continued)").format(title=title)
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            if get_pages:
                return pages
            else:
                await self.send_pages(ctx, pages, embed=True, help_settings=help_settings)
        else:
            await ctx.send(_("You need to enable embeds to use the help menu"))

    async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings):
        coms = await self.get_cog_help_mapping(ctx, obj, help_settings=help_settings)
        if not (coms or help_settings.verify_exists):
            return

        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx)

            if description := obj.format_help_for_context(ctx):
                emb["embed"]["description"] = "**" + description + "**"

            for name, command in sorted(coms.items()):
                emb["fields"].append(
                    EmbedField(name, command.format_shortdoc_for_context(ctx) or "\N{ZWSP}", False)
                )

            pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
            await self.send_pages(
                ctx,
                pages,
                embed=True,
                help_settings=help_settings,
            )
        else:
            await ctx.send(_("You need to enable embeds to use the help menu"))
