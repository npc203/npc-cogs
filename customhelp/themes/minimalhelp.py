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
    cast,
)


class MinimalHelp:
    async def format_bot_help(self, ctx: Context, help_settings: HelpSettings):
        description = ctx.bot.description or ""
        tagline = (help_settings.tagline) or self.get_default_tagline(ctx)
        full_text = f"{description}\n\n{tagline}"
        # Maybe add category desc somewhere?
        for cat in GLOBAL_CATEGORIES:
            coms = await self.get_category_help_mapping(
                ctx, cat, help_settings=help_settings
            )
            all_cog_text = ""
            for _, data in coms:
                all_cog_text += " · ".join(f"{name}" for name in data) + " · "

            full_text += f"\n\n__**{cat.name}**__: {all_cog_text}"
        for page in pagify(full_text):
            await ctx.send(page)

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
        full_text = f"{description}\n\n{tagline}\n\n"
        for _, data in coms:
            full_text += "\n".join(
                f"{ctx.prefix}{name} – {command.format_shortdoc_for_context(ctx)}"
                for name, command in data.items()
            )
            full_text += "\n"
        for page in pagify(full_text):
            await ctx.send(page)