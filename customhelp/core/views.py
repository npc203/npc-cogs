import discord
from typing import List
from .category import get_category
from . import ARROWS
from redbot.core import commands


# PICKER MENUS
class MenuPicker(discord.ui.Select):
    def __init__(self, options, configset):
        self.configset = configset
        super().__init__(
            placeholder="Choose one of the following options...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.configset.set(self.values[0].lower())
        await interaction.message.edit(  # type: ignore
            content=f"The menu type is set to type: `{self.values[0]}`", view=None
        )
        self.view.stop()  # type:ignore


class MenuView(discord.ui.View):
    def __init__(self, uid, options, configset):
        super().__init__(timeout=120)
        self.uid = uid
        self.message = None
        self.add_item(MenuPicker(options, configset))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.uid:  # type:ignore
            return True
        else:
            await interaction.response.send_message(
                "You are not allowed to interact with this menu.", ephemeral=True
            )
            return False

    async def on_timeout(self) -> None:
        pass
        # self.edit(content="Menu timed out.", view=None)


# HELP MENUS
class BaseInteractionMenu(discord.ui.View):
    def __init__(self, pages, options, help_settings, bypass_checks, timeout=120):
        self.cache = {}
        self.help_settings = help_settings
        self.bypass_checks = bypass_checks
        self.pages = pages
        self.curr_page = 0
        self.max_page = len(pages)
        super().__init__(timeout=timeout)

        if options:
            select_bar = SelectHelpBar(options)
            self.add_item(select_bar)

        arrows = [DoubleLeftButton, LeftButton, DeleteButton, RightButton, DoubleRightButton]
        for arrow in arrows:
            obj = arrow()
            self.add_item(obj)
            obj.setup()

    async def start(self, ctx: commands.Context, usereply: bool = True):
        # TODO Confidently embeds lol, generalize this
        if usereply:
            self.message = await ctx.reply(embed=self.pages[0], view=self, mention_author=False)
        else:
            self.message = await ctx.send(embed=self.pages[0], view=self)
        self.ctx = ctx
        self.valid_ids = list(ctx.bot.owner_ids)
        self.valid_ids.append(ctx.author.id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.valid_ids:  # type:ignore
            return True
        else:
            await interaction.response.send_message(
                "You cannot use this help menu.", ephemeral=True
            )
            return False

    def change_source(self, new_source):
        self.pages = new_source
        self.max_page = len(new_source)
        self.curr_page = 0
        if self.max_page > 1:
            self.children[-2].disabled = False  # type: ignore right arrow

        if self.max_page > 2:
            self.children[-1].disabled = False  # type: ignore double right arrow


class BaseButton(discord.ui.Button):
    view: BaseInteractionMenu

    def __init__(self, emoji, style=discord.ButtonStyle.secondary):
        super().__init__(emoji=emoji, style=style, row=4)

    def edit_buttons(self) -> bool:
        raise NotImplementedError

    def setup(self):
        raise NotImplementedError

    async def callback(self, interaction: discord.Interaction):
        if self.edit_buttons():
            await interaction.response.defer()
            await self.view.message.edit(
                embed=self.view.pages[self.view.curr_page], view=self.view
            )


class DeleteButton(BaseButton):
    def __init__(self):
        super().__init__(emoji=ARROWS["cross"])

    def setup(self):
        pass

    def edit_buttons(self):
        self.view.ctx.bot.loop.create_task(self.view.message.delete())
        self.view.stop()
        return False


class LeftButton(BaseButton):
    def __init__(self):
        super().__init__(emoji=ARROWS["left"])

    def setup(self):
        if self.view.curr_page == 0:
            self.disabled = True

    def edit_buttons(self):
        view: BaseInteractionMenu = self.view

        if view.curr_page > 0:
            view.curr_page -= 1
            view.children[-1].disabled = False  # type: ignore double right arrow
            view.children[-2].disabled = False  # type: ignore right arrow

        if view.curr_page == 0:
            self.disabled = True

        if view.curr_page == 1:
            view.children[-5].disabled = True  # type: ignore double left arrow

        return True


class RightButton(BaseButton):
    def __init__(self):
        super().__init__(emoji=ARROWS["right"])

    def setup(self):
        if self.view.curr_page == self.view.max_page - 1:
            self.disabled = True

    def edit_buttons(self):
        view: BaseInteractionMenu = self.view

        if view.curr_page < view.max_page - 1:
            view.curr_page += 1
            view.children[-5].disabled = False  # type: ignore double left arrow
            view.children[-4].disabled = False  # type: ignore left arrow

        if view.curr_page == view.max_page - 1:
            self.disabled = True

        if view.curr_page == view.max_page - 2:
            view.children[-1].disabled = True  # type: ignore double right arrow

        return True


class DoubleLeftButton(BaseButton):
    def __init__(self):
        super().__init__(emoji=ARROWS["force_left"])

    def setup(self):
        self.disabled = True

    def edit_buttons(self):
        view: BaseInteractionMenu = self.view

        if view.curr_page != 0:
            view.curr_page = 0
            self.disabled = True
            view.children[-1].disabled = False  # type: ignore double right arrow
            view.children[-2].disabled = False  # type: ignore right arrow
            view.children[-4].disabled = True  # type: ignore left arrow
            return True
        else:
            return False  # Already in the first page, no need to refresh


class DoubleRightButton(BaseButton):
    def __init__(self):
        super().__init__(emoji=ARROWS["force_right"])

    def setup(self):
        if self.view.max_page <= 2:
            self.disabled = True

    def edit_buttons(self):
        view: BaseInteractionMenu = self.view

        if view.curr_page != view.max_page - 1:
            view.curr_page = view.max_page - 1
            self.disabled = True
            view.children[-5].disabled = False  # type: ignore double left arrow
            view.children[-4].disabled = False  # type: ignore left arrow
            view.children[-2].disabled = True  # type: ignore right arrow
            return True
        else:
            return False  # Already in the last page, no need to refresh


# Selection Bar
class SelectHelpBar(discord.ui.Select):
    view: BaseInteractionMenu

    def __init__(self, categories: List[discord.SelectOption]):
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=categories,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):

        # Cache categories
        name = self.values[0].lower()
        if not (category_pages := self.view.cache.get(name, None)):
            category_name = get_category(name)
            self.view.cache[
                name
            ] = category_pages = await self.view.ctx.bot._help_formatter.format_category_help(
                self.view.ctx,
                category_name,
                self.view.help_settings,
                get_pages=True,
                bypass_checks=self.view.bypass_checks,
            )

        await interaction.response.defer()
        if category_pages:
            self.view.change_source(category_pages)
            await self.view.message.edit(embed=category_pages[self.view.curr_page], view=self.view)


# class DropdownView(discord.ui.View):
#     def __init__(self, cats, message: discord.Message = None, **kwargs: Any):
#         super().__init__(timeout=60)
#         self.message = message
#         self.ctx = kwargs.get("ctx", None)
#         self.config = kwargs.get("config", None)

#         # Adds the dropdown to our view object.
#         self.add_item(Dropdown(cats=cats, ctx=self.ctx, config=self.config))

#     async def on_timeout(self):
#         for item in self.children:
#             item.disabled = True
#         #  self.clear_items()
#         with contextlib.suppress(discord.NotFound):
#             await self.message.edit(view=self)
#         self.stop()

#     async def interaction_check(self, interaction: discord.Interaction):
#         """Just extends the default reaction_check to use owner_ids"""
#         if interaction.message.id != self.message.id:
#             await interaction.response.send_message(
#                 content=_("You are not authorized to interact with this."),
#                 ephemeral=True,
#             )
#             return False
#         if interaction.user.id not in (*self.ctx.bot.owner_ids, self.ctx.author.id):
#             await interaction.response.send_message(
#                 content=_("This is not your help menu. \U0001f928"),
#                 ephemeral=True,
#             )
#             return False
#         return True
