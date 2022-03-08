import discord
from typing import List, Optional, TYPE_CHECKING

import customhelp.core.base_help as base_help

from .category import get_category
from . import ARROWS
from redbot.core import commands
import enum

if TYPE_CHECKING:
    from customhelp.core.base_help import BaguetteHelp


class ComponentType(enum.IntEnum):
    MENU = 0
    ARROW = 1


# PICKER MENUS (Stuff for selecting buttons, select etc)
class MenuView(discord.ui.View):
    def __init__(self, uid, config, callback):
        super().__init__(timeout=120)
        self.uid = uid
        self.message: discord.Message
        self.update_callback = callback
        self.config = config
        self.values: List[Optional[str]] = [None, None]  # menutype value,arrowtype value

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.uid:  # type:ignore
            return True
        else:
            await interaction.response.send_message(
                "You are not allowed to interact with this menu.", ephemeral=True
            )
            return False

    @discord.ui.button(label="Accept", emoji="✅", style=discord.ButtonStyle.success, row=2)
    async def accept(self, button, interaction):
        if self.values.count(None) == len(self.values):
            return await self.message.edit(content="No value selected.")

        final_message = ""
        for ind, val in enumerate(self.values):
            name = ComponentType(ind).name
            if val:
                final_message += f"Selected {name.lower()}type: {val}\n"
                await getattr(self.config, name.lower() + "type").set(val.lower())
                self.update_callback("settings", name.lower() + "type", val)

        await interaction.message.edit(content=final_message, view=None)

        self.stop()

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.danger, row=2)
    async def cancel(self, button, interaction):
        await self.message.edit(content="Selection cancelled.", view=None)
        self.stop()

    async def on_timeout(self) -> None:
        await self.message.edit(content="Selection timed out.", view=None)


class MenuPicker(discord.ui.Select):
    view: MenuView

    def __init__(self, menutype, options):
        self.menutype: ComponentType = menutype
        super().__init__(
            placeholder=f"Select {self.menutype.name.lower()}type",
            min_values=1,
            max_values=1,
            options=options,
            row=self.menutype,  # HACKS
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.values[self.menutype] = self.values[0]


# HELP MENU Interaction items
class BaseInteractionMenu(discord.ui.View):
    def __init__(
        self,
        pages,
        help_settings,
        bypass_checks,
        timeout=120,
        *,
        hmenu,
    ):
        self.cache = {}
        self.help_settings = help_settings
        self.bypass_checks = bypass_checks
        self.pages = pages
        self.curr_page = 0
        self.max_page = len(pages)
        self.children: List = []
        self.hmenu: base_help.HybridMenus = hmenu

        super().__init__(timeout=timeout)

    def update_buttons(self):
        pass

    def _get_kwargs_from_page(self, value):
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return {"embed": value, "content": None}
        return {}

    async def on_timeout(self):
        children = []
        for child in self.children:
            if isinstance(child, SelectHelpBar):
                child.disabled = True
                children.append(child)
        self.children = children
        try:
            await self.message.edit(view=self)
        except discord.NotFound:  # User unloaded the cog
            pass

    async def start(
        self, ctx: commands.Context, message: discord.Message = None, use_reply: bool = True
    ):
        if message is None:
            if use_reply:
                self.message = await ctx.reply(
                    **self._get_kwargs_from_page(self.pages[0]), view=self, mention_author=False
                )
            else:
                self.message = await ctx.send(
                    **self._get_kwargs_from_page(self.pages[0]), view=self
                )
        else:
            self.message = message
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
        self.curr_page = 0
        self.max_page = len(new_source)


class ReactButton(discord.ui.Button):
    view: BaseInteractionMenu

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if not isinstance(view.ctx.bot._help_formatter, BaguetteHelp):
            self.view.hmenu.stop()
            return

        # Cache categories
        name = self.custom_id  # type:ignore
        if not (category_pages := view.cache.get(name, None)):
            if name == "home":
                category_pages = await view.ctx.bot._help_formatter.format_bot_help(
                    view.ctx, view.help_settings, get_pages=True
                )
            else:
                category_obj = get_category(name)
                if not category_obj:
                    return
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

    async def callback(self, interaction):  # TODO
        pass
