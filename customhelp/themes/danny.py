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
)


class DannyHelp:
    async def format_bot_help(self, ctx: Context, help_settings: HelpSettings):
        coms = await self.get_bot_help_mapping(ctx, help_settings=help_settings)
        await helper(self, ctx, help_settings, coms)

    async def format_category_help(
        self, ctx: Context, obj: CategoryConvert, help_settings: HelpSettings
    ):
        coms = await self.get_category_help_mapping(
            ctx, obj, help_settings=help_settings
        )
        await helper(self, ctx, help_settings, coms)


async def helper(self, ctx: Context, help_settings: HelpSettings, coms):

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
            emb["embed"]["title"] = f"*{description[:250]}*"
        for cog_name, data in coms:
            if cog_name:
                title = f"**{cog_name}**"
            else:
                title = _("**No Category:**")

            cog_text = "\n" + " ".join(
                (f"`{name}`") for name, command in sorted(data.items())
            )

            for i, page in enumerate(pagify(cog_text, page_length=1000, shorten_by=0)):
                field = EmbedField(title, page, True)
                emb["fields"].append(field)

        await self.make_and_send_embeds(ctx, emb, help_settings=help_settings)

    else:
        await ctx.send("Please have embeds enabled")
