from ..abc import ThemesMeta
from ..core.base_help import (
    EMPTY_STRING, GLOBAL_CATEGORIES, CategoryConvert, Context, EmbedField,
    HelpSettings, _, pagify)


class TwinHelp(ThemesMeta):
    """This help is designed by TwinShadow a.k.a TwinShadow#0666"""

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
            if description:
                splitted = description.split("\n\n")
                name = splitted[0]
                value = "\n\n".join(splitted[1:])
                if not value:
                    value = EMPTY_STRING
                field = EmbedField(name[:252], value[:1024], False)
                emb["fields"].append(field)

            emb["title"] = f"{ctx.me.name} Help Menu"
            for cat in GLOBAL_CATEGORIES:
                if cat.cogs and await self.blacklist(ctx, cat.name):
                    cog_names = "`" + "` `".join(cat.cogs) + "`" if cat.cogs else ""
                    for i, page in enumerate(pagify(cog_names, page_length=1000, shorten_by=0)):
                        if i == 0:
                            title = (str(cat.reaction) or "") + f"  __{cat.name.capitalize()}:__ "
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
                    title = f"__**{cog_name}**__"
                else:
                    title = _("**No Category:**")
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
            # fix this
            await ctx.send("Kindly enable embeds")
