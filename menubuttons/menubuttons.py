import asyncio
import logging

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import pagify

from .menu_new import MenuMixin
from .utils import emoji_converter, parse_yaml, quick_emoji_converter

log = logging.getLogger("red.npc-cogs.menubuttons")


class MenuButtons(MenuMixin, commands.Cog):
    """
    Red menus to buttons + support for custom menu emojis
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

        # Config things
        self.config: Config = Config.get_conf(
            self,
            identifier=32674893924237,
            force_registration=True,
        )
        self.default_arrows = {
            "left": "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
            "right": "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}",
            "cross": "\N{CROSS MARK}",
        }
        self.config.register_global(
            arrows=self.default_arrows,
            toggle=False,
        )
        self.map_conf_arrows = {
            "left": menus.prev_page,
            "right": menus.next_page,
            "cross": menus.close_menu,
        }

        # Cache
        # self.conf_toggle = False

        # old menu stuff backup
        self.old_controls = menus.DEFAULT_CONTROLS.copy()
        self.old_menu = menus.menu

        # proper init stuff
        self._ready = asyncio.Event()
        self._init_task = None
        self._ready_raised = False

    # Oh jack, sweet jackenmen https://discord.com/channels/133049272517001216/160386989819035648/666985042136006670
    def create_init_task(self):
        def _done_callback(task):
            exc = task.exception()
            if exc is not None:
                log.error(
                    "An unexpected error occurred during CogName's initialization.", exc_info=exc
                )
                self._ready_raised = True
            self._ready.set()

        self._init_task = asyncio.create_task(self.initialize())
        self._init_task.add_done_callback(_done_callback)

    async def initialize(self):
        # alternatively use wait_until_red_ready() if you need some stuff that happens in our post-connection startup
        await self.bot.wait_until_ready()
        toggle = await self.config.toggle()
        if toggle:
            menus.menu = self.new_button_menu
        await self.refresh_arrows()

    async def refresh_arrows(self):
        raw_arrows = await self.config.arrows()
        def_ctrls = menus.DEFAULT_CONTROLS
        def_ctrls.clear()

        for name, emoji in raw_arrows:
            if valid_emoji := quick_emoji_converter(self.bot, emoji):
                def_ctrls[valid_emoji] = self.map_conf_arrows[name]
            else:
                def_ctrls[self.default_arrows[name]] = self.map_conf_arrows[name]
                log.warn("The {} arrow emoji {} is not found by the bot".format(name, emoji))

    def cog_unload(self):
        if self._init_task is not None:
            self._init_task.cancel()

        menus.menu = self.old_menu
        menus.DEFAULT_CONTROLS = self.old_controls

    async def cog_before_invoke(self, ctx):
        # use if commands need initialize() to finish
        async with ctx.typing():
            await self._ready.wait()
        if self._ready_raised:
            await ctx.send(
                "There was an error during CogName's initialization. Check logs for more information."
            )
            raise commands.CheckFailure()

    @commands.is_owner()
    @commands.group()
    async def buttons(self, ctx):
        """Base menubuttons command"""

    @buttons.command()
    async def toggle(self, ctx, toggle: bool):
        """Toggle between button menus and normal red ones"""
        await self.config.toggle.set(toggle)
        if toggle:
            menus.menu = self.new_button_menu
        else:
            menus.menu = self.old_menu
        await ctx.send(f"Sucessfully {'en' if toggle else 'dis'}abled button menus")

    @buttons.command()
    async def refresh(self, ctx):
        """Refresh the menu buttons, incase they don't show up"""
        await self.refresh_arrows()
        await ctx.tick()

    @buttons.command()
    async def show(self, ctx):
        """Show your current menu configuration"""
        emb = discord.Embed(title="Current red menu settings")
        await ctx.send(embed=emb)

    @buttons.command(aliases=["arrow"])
    async def arrows(self, ctx, *, correct_txt=None):
        """Add custom arrows for fun and profit"""
        if correct_txt:
            content = correct_txt
        else:
            await ctx.send(
                "Your next message should be with the specfied format as follows(see docs for more info).\n"
                "**If you enter an invalid emoji your help will break.**\n"
                "Example:\n"
                "left :\n"
                " - emoji: ↖️\n"
                " - style: success\n"
                " - label: 'text is cool'\n"
                "Note: The other arrows are `right`,`cross`, `home`, `force_left` and `force_right`"
            )
            try:
                msg = await self.bot.wait_for(
                    "message",
                    timeout=180,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                )
                content = msg.content
            except asyncio.TimeoutError:
                return await ctx.send("Timed out, please try again.")

        if not (yaml_data := await parse_yaml(ctx, content)):
            return

        already_present_emojis = [
            quick_emoji_converter(self.bot, arrow)
            for arrow in menus.DEFAULT_CONTROLS.keys()
            if arrow
        ]

        parsed = {}
        failed = []  # [(reason for failure,arrow_name)]
        check = ("emoji", "label", "style")
        check_name = (
            "left",
            "right",
            "cross",
            "home",
        )  # Maybe later add "force_right", "force_left"
        check_style = ["primary", "secondary", "success", "danger"]

        parsed_data = {}
        for k, v in yaml_data.items():
            tmp = {}
            for val in v:
                final_key, final_val = val.popitem()
                tmp[final_key] = final_val
            parsed_data[k] = tmp

        for arrow, details in parsed_data.items():
            if arrow not in check_name:
                failed.append(("Invalid arrow name", arrow))
            else:
                parsed[arrow] = details

                # Junk
                remove_key = []
                for key in details:
                    if key not in check:
                        failed.append(((key, "Invalid key"), arrow))
                        remove_key.append(key)
                for key in remove_key:
                    details.pop(key)

                # Emoji verify
                if emoji := details.pop("emoji", None):
                    converted = await emoji_converter(ctx, emoji)
                    if converted:
                        if emoji in already_present_emojis:
                            failed.append((("emoji", "Emoji already present as arrow"), arrow))
                        else:
                            parsed[arrow]["emoji"] = converted
                    else:
                        failed.append((("emoji", "Bot can't react this arrow"), arrow))

                # ButtonStyle verify
                if style := details.pop("style", None):
                    if style in check_style:
                        parsed[arrow]["style"] = style
                    else:
                        failed.append((("button", "Invalid button style"), arrow))

        async with self.config.arrows() as conf:
            for name, modified_values in parsed.items():
                for arrow in conf:
                    if arrow["name"] == name:
                        arrow.update(modified_values)
                        break

        for page in pagify(
            "Successfully added the edits"
            if not failed
            else "The following things failed:\n"
            + "\n".join(
                [
                    f"`{reason[0]}` failed in `{arrow}`, `Reason: {reason[1]}`"
                    for reason, arrow in failed
                ]
            )
        ):
            await ctx.send(page)
        await self.refresh_arrows()

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        return
