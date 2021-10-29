from contextvars import Context
import discord
from typing import List
from .category import get_category


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
        await interaction.edit_original_message(  # type: ignore
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


class SelectHelp(discord.ui.View):
    def __init__(self, uid, options, configset):
        super().__init__(timeout=120)
        self.uid = uid
        self.add_item(MenuPicker(options, configset))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.uid:  # type:ignore
            return True
        else:
            await interaction.response.send_message(
                "You cannot use this help menu.", ephemeral=True
            )
            return False

    async def on_timeout(self) -> None:
        pass
        # self.edit(content="Menu timed out.", view=None)


class BaseHelpMenu(discord.ui.View):
    def __init__(self, pages):
        self.cache = {}


class SelectHelpBar(discord.ui.Select):
    view: BaseHelpMenu

    def __init__(self, categories: List[discord.SelectOption]):
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=categories,
        )

    async def callback(self, interaction: discord.Interaction):

        # Cache categories
        name = self.values[0].lower()
        if not (category := self.view.cache.get(name)):
            category = get_category(name)
            self.view.cache[name] = category

        # TODO

        await interaction.response.defer()
        await interaction.edit_original_message()


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
