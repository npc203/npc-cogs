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


class DankHelp:
    async def format_bot_help(self, ctx: Context, help_settings: HelpSettings):
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
            emb["embed"]["description"] = description

            category_text = ""
            emb["title"] = f"{ctx.me.name} Help Menu"
            # Maybe add category desc somewhere?
            for cat in GLOBAL_CATEGORIES:
                title = (
                    cat.reaction + " " if cat.reaction else ""
                ) + cat.name.capitalize()
                emb["fields"].append(
                    EmbedField(title, f"`{ctx.prefix}help {cat.name}`", True)
                )
        await self.make_and_send_embeds(ctx, emb, help_settings=help_settings)

    async def format_category_help(
        self, ctx: Context, obj: CategoryConvert, help_settings: HelpSettings
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

            emb["embed"]["title"] = (
                obj.reaction if obj.reaction else ""
            ) + obj.name.capitalize()
            emb["footer"]["text"] = tagline
            if description:
                emb["embed"]["description"] = f"*{description[:250]}*"

            all_cog_text = ""
            for cog_name, data in coms:
                all_cog_text += "\n" + ",".join(
                    f"`{name}`" for name, command in sorted(data.items())
                )
            for i, page in enumerate(
                pagify(all_cog_text, page_length=1000, shorten_by=0)
            ):
                field = EmbedField(
                    EMPTY_STRING,
                    page,
                    False,
                )
                emb["fields"].append(field)

            await self.make_and_send_embeds(ctx, emb, help_settings=help_settings)
        else:
            await ctx.send("Enable embeds please")
