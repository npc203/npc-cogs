from ..abc import ThemesMeta
from ..core.base_help import (
    EMPTY_STRING, GLOBAL_CATEGORIES, CategoryConvert, Context, EmbedField,
    HelpSettings, _, chain, commands, pagify)


class Mixture(ThemesMeta):
    """This is a mixture of other themes, a variant filling the lacking features of others"""

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
                                str(cat.reaction) if cat.reaction else ""
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
                emb["embed"]["description"] = f"*{description[:250]}*"

            spacer_list = chain(*(i[1].keys() for i in coms))
            spacing = len(max(spacer_list, key=len))

            def shorten_line(a_line: str) -> str:
                if len(a_line) < 70:  # embed max width needs to be lower
                    return a_line
                return a_line[:67] + "..."

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
            # fix this
            await ctx.send("Kindly enable embeds")

    async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings):

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
                emb["embed"]["description"] = "**" + description + "**"
            if coms:
                for name, command in sorted(coms.items()):
                    emb["fields"].append(
                        EmbedField(name, command.format_shortdoc_for_context(ctx), False)
                    )

                pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
                await self.send_pages(
                    ctx,
                    pages,
                    embed=True,
                    help_settings=help_settings,
                )
        else:
            await ctx.send(f"Enable embeds please")
