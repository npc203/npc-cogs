from redbot.core.utils.chat_formatting import box
from tabulate import tabulate

from ..abc import ThemesMeta
from ..core.base_help import (
    EMPTY_STRING,
    Category,
    Context,
    EmbedField,
    HelpSettings,
    commands,
    pagify,
)

grouper = lambda a, n: [a[k : k + n] for k in range(0, len(a), n)]


class Blocks(ThemesMeta):
    """Max's Suggestion to add something new I believe >_>"""

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
        all_cog_text = []

        for cog_name, data in coms:
            all_cog_text.extend(map(lambda x: ctx.clean_prefix + x, data.keys()))

        all_cog_str = tabulate(
            grouper(all_cog_text, 3),
            tablefmt="plain",
        )

        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx)
            emb["embed"]["title"] = (
                (str(obj.reaction) if obj.reaction else "") + " " + obj.name.capitalize()
            )

            if description := obj.long_desc:
                emb["embed"]["description"] = f"{description[:250]}"

            for page in pagify(all_cog_str, page_length=998, shorten_by=0):
                field = EmbedField(
                    EMPTY_STRING,
                    box(page),
                    False,
                )
                emb["fields"].append(field)

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
        else:
            await self.send_pages(
                ctx,
                list(map(box, pagify(all_cog_str, shorten_by=0, page_length=2042))),
                embed=False,
                help_settings=help_settings,
            )

    async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings):
        coms = await self.get_cog_help_mapping(ctx, obj, help_settings=help_settings)
        if not (coms or help_settings.verify_exists):
            return

        description = obj.format_help_for_context(ctx)

        cmd_list = tabulate(
            grouper(list(map(lambda x: ctx.clean_prefix + x, sorted(coms.keys()))), 3),
            tablefmt="plain",
        )

        if await ctx.embed_requested():
            emb = await self.embed_template(help_settings, ctx)
            if description:
                emb["embed"]["description"] = "**" + description + "**"
            if coms:
                for page in pagify(cmd_list, page_length=998, shorten_by=0):
                    emb["fields"].append(EmbedField(EMPTY_STRING, box(page), False))

                pages = await self.make_embeds(ctx, emb, help_settings=help_settings)
                await self.send_pages(
                    ctx,
                    pages,
                    embed=True,
                    help_settings=help_settings,
                )
        else:
            await self.send_pages(
                ctx,
                list(map(box, pagify(cmd_list, shorten_by=0, page_length=2042))),
                embed=False,
                help_settings=help_settings,
            )
