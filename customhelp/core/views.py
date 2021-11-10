import discord
from typing import List, Union

from .category import get_category
from . import ARROWS
from redbot.core import commands


# PICKER MENUS
class MenuView(discord.ui.View):
    def __init__(self, uid, options, configset, callback):
        super().__init__(timeout=120)
        self.uid = uid
        self.message: discord.Message
        self.update_callback = callback
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
        await self.message.edit(content="Menu timed out.", view=None)


class MenuPicker(discord.ui.Select):
    view: MenuView

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
        self.view.update_callback("settings", "menutype", self.values[0].lower())
        self.view.stop()  # type:ignore


# HELP MENU Interaction items
class BaseInteractionMenu(discord.ui.View):
    def __init__(self, pages, help_settings, bypass_checks, timeout=120, nav=True):
        self.cache = {}
        self.help_settings = help_settings
        self.bypass_checks = bypass_checks
        self.pages = pages
        self.curr_page = 0
        self.max_page = len(pages)

        super().__init__(timeout=timeout)
        self.children: List[Union[BaseButton, SelectHelpBar]] = []

        if nav:
            arrows = [DoubleLeftButton, LeftButton, DeleteButton, RightButton, DoubleRightButton]
            for arrow in arrows:
                obj = arrow()
                self.add_item(obj)
                obj.setup()

    async def on_timeout(self):
        new_children = []
        for child in self.children:
            if isinstance(child, SelectHelpBar):
                child.disabled = True
                new_children.append(child)
        self.children = new_children
        await self.message.edit(view=self)

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
            self.children[-2].disabled = False  # right arrow

        if self.max_page > 2:
            self.children[-1].disabled = False  # double right arrow


class ReactButton(discord.ui.Button):
    view: BaseInteractionMenu

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def callback(
        self, interaction: discord.Interaction
    ):  # Code duplication! same as the callback from select at the bottom
        view = self.view

        # Cache categories
        name = self.custom_id.lower()  # type:ignore
        if not (category_pages := view.cache.get(name, None)):
            if name == "home":
                category_pages = await view.ctx.bot._help_formatter.format_bot_help(
                    view.ctx, view.help_settings, get_pages=True
                )
            else:
                category_obj = get_category(name)
                view.cache[
                    name
                ] = category_pages = await view.ctx.bot._help_formatter.format_category_help(
                    view.ctx,
                    category_obj,
                    view.help_settings,
                    get_pages=True,
                    bypass_checks=view.bypass_checks,
                )

        await interaction.response.defer()
        if category_pages:
            view.change_source(category_pages)
            await view.message.edit(embed=category_pages[view.curr_page], view=view)


class BaseButton(discord.ui.Button):
    view: BaseInteractionMenu

    def __init__(self, **kwargs):
        super().__init__(**kwargs, row=4)

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
        super().__init__(**ARROWS["cross"])

    def setup(self):
        pass

    def edit_buttons(self):
        self.view.ctx.bot.loop.create_task(self.view.message.delete())
        self.view.stop()
        return False


class LeftButton(BaseButton):
    def __init__(self):
        super().__init__(**ARROWS["left"])

    def setup(self):
        if self.view.curr_page == 0:
            self.disabled = True

    def edit_buttons(self):
        view: BaseInteractionMenu = self.view

        if view.curr_page > 0:
            view.curr_page -= 1
            view.children[4].disabled = False  # double right arrow
            view.children[3].disabled = False  # right arrow

        if view.curr_page == 0:
            self.disabled = True

        if view.curr_page == 1:
            view.children[0].disabled = True  # double left arrow

        return True


class RightButton(BaseButton):
    def __init__(self):
        super().__init__(**ARROWS["right"])

    def setup(self):
        if self.view.curr_page == self.view.max_page - 1:
            self.disabled = True

    def edit_buttons(self):
        view: BaseInteractionMenu = self.view

        if view.curr_page < view.max_page - 1:
            view.curr_page += 1
            view.children[0].disabled = False  # double left arrow
            view.children[1].disabled = False  # left arrow

        if view.curr_page == view.max_page - 1:
            self.disabled = True

        if view.curr_page == view.max_page - 2:
            view.children[4].disabled = True  # double right arrow

        return True


class DoubleLeftButton(BaseButton):
    def __init__(self):
        super().__init__(**ARROWS["force_left"])

    def setup(self):
        self.disabled = True

    def edit_buttons(self):
        view: BaseInteractionMenu = self.view

        if view.curr_page != 0:
            view.curr_page = 0
            self.disabled = True
            view.children[4].disabled = False  # double right arrow
            view.children[3].disabled = False  # right arrow
            view.children[1].disabled = True  # left arrow
            return True
        else:
            return False  # Already in the first page, no need to refresh


class DoubleRightButton(BaseButton):
    def __init__(self):
        super().__init__(**ARROWS["force_right"])

    def setup(self):
        if self.view.max_page <= 2:
            self.disabled = True

    def edit_buttons(self):
        view: BaseInteractionMenu = self.view

        if view.curr_page != view.max_page - 1:
            view.curr_page = view.max_page - 1
            self.disabled = True
            view.children[0].disabled = False  # double left arrow
            view.children[1].disabled = False  # left arrow
            view.children[3].disabled = True  # right arrow
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
        view = self.view

        # Cache categories
        name = self.values[0].lower()
        if not (category_pages := view.cache.get(name, None)):
            if name == "home":
                category_pages = await view.ctx.bot._help_formatter.format_bot_help(
                    view.ctx, view.help_settings, get_pages=True
                )
            else:
                category_obj = get_category(name)
                view.cache[
                    name
                ] = category_pages = await view.ctx.bot._help_formatter.format_category_help(
                    view.ctx,
                    category_obj,
                    view.help_settings,
                    get_pages=True,
                    bypass_checks=view.bypass_checks,
                )

        await interaction.response.defer()
        if category_pages:
            view.change_source(category_pages)
            await view.message.edit(embed=category_pages[view.curr_page], view=view)
