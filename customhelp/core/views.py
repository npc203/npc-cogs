import enum
import logging
from typing import TYPE_CHECKING, List, Optional

import discord
from redbot.core import commands

if TYPE_CHECKING:
    import customhelp.core.base_help as base_help

LOG = logging.getLogger("red.customhelp.core.views")


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
    async def accept(self, interaction, button):
        if self.values.count(None) == len(self.values):
            return await self.message.edit(content="No value selected.")

        final_message = ""
        for ind, val in enumerate(self.values):
            name = ComponentType(ind).name
            if val:
                final_message += f"Selected {name.lower()}type: {val}\n"
                await getattr(self.config, name.lower() + "type").set(val.lower())
                self.update_callback("settings", name.lower() + "type", val.lower())

        await interaction.message.edit(content=final_message, view=None)

        self.stop()

    @discord.ui.button(label="Cancel", emoji="✖", style=discord.ButtonStyle.danger, row=2)
    async def cancel(self, interaction, button):
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
        await interaction.response.defer()


# HELP MENU Interaction items
class BaseInteractionMenu(discord.ui.View):
    def __init__(self, *, hmenu):
        self.hmenu: base_help.HybridMenus = hmenu
        super().__init__(timeout=hmenu.settings["timeout"])

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
        # Filter select bars and disable them
        for child in self.children:
            if isinstance(child, discord.ui.Select):
                child.disabled = True
                children.append(child)

        self.clear_items()
        for child in children:
            self.add_item(child)

        try:
            await self.message.edit(view=self)
        except discord.NotFound:  # User unloaded the cog
            pass

    async def start(
        self,
        ctx: commands.Context,
        message: Optional[discord.Message] = None,
    ):
        if message is None:
            if self.hmenu.settings["replies"]:
                self.message = await ctx.send(
                    **self._get_kwargs_from_page(self.hmenu.pages[0]),
                    view=self,
                    mention_author=False,
                    reference=ctx.message.to_reference(
                        fail_if_not_exists=False
                    ),
                )
            else:
                self.message = await ctx.send(
                    **self._get_kwargs_from_page(self.hmenu.pages[0]), view=self
                )
        else:
            self.message = message
        self.ctx = ctx
        self.valid_ids = list(ctx.bot.owner_ids)  # type: ignore
        self.valid_ids.append(ctx.author.id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.valid_ids:
            return True
        else:
            await interaction.response.send_message(
                "You cannot use this help menu.", ephemeral=True
            )
            return False


class ReactButton(discord.ui.Button):
    view: BaseInteractionMenu

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.custom_id: str

    async def callback(self, interaction: discord.Interaction):
        await self.view.hmenu.category_react_action(self.view.ctx, interaction, self.custom_id)


# Selection Bar
class SelectMenuHelpBar(discord.ui.Select):
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
        await self.view.hmenu.category_react_action(self.view.ctx, interaction, self.values[0])


class SelectArrowHelpBar(discord.ui.Select):
    view: BaseInteractionMenu

    def __init__(self, arrows: List[discord.SelectOption]):
        super().__init__(
            placeholder="Select an arrow...",
            min_values=1,
            max_values=1,
            options=arrows,
        )

    async def callback(self, interaction):
        if self.values:
            if self.values[0] == "Home":
                await self.view.hmenu.category_react_action(self.view.ctx, interaction, "home")
            await self.view.hmenu.arrow_emoji_button[self.values[0]](interaction)
