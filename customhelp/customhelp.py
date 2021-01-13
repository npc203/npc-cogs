from typing import Literal, Union
from itertools import chain
import yaml
import asyncio
import discord
from discord.ext import commands as dpy_commands
from redbot.core.utils import menus
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core import Config
from .core.base_help import BaguetteHelp
from .core.category import Category, GLOBAL_CATEGORIES
from emoji import UNICODE_EMOJI
from . import themes
from types import MethodType
from tabulate import tabulate

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

_ = Translator("Help", __file__)

# Rememeber cache pages, obselete cause help changes with user.
# Swtichable alphabetic ordered display
# No cog commands still to add
# For all the bunch config calls, do I need it? it's just the bot owner usage!
"""
Config Structure:
    {
      "categories":
      [
            {
                "name" : name 
                "desc" : desc
                "cogs" : []
                "reaction":None
            }
     ]
    }
"""


class CustomHelp(commands.Cog):
    """
    A custom customisable help
    """

    __author__ = ["npc203"]
    __version__ = "0.0.1"

    def __init__(self, bot: Red):
        self.bot = bot
        self.feature_list = {
            "category": "format_category_help",
            "main": "format_bot_help",
            "cog": "format_cog_help",
            "command": "format_command_help",
        }
        self.config = Config.get_conf(
            self,
            identifier=278198241009,
            force_registration=True,  # I'm gonna regret this
        )
        self.chelp_global = {
            "categories": [],
            "theme": {"cog": None, "category": None, "command": None, "main": None},
            "uncategorised": {"name": None, "desc": None, "reaction": None},
        }
        self.config.register_global(**self.chelp_global)

    def cog_unload(self):
        self.bot.reset_help_formatter()

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """
        Thanks Sinbad!
        """
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    """
    #Is this better?
    async def cog_check(self, ctx):
        return self.bot.is_owner(ctx.author)
    """

    async def refresh_cache(self):
        # Blocking?
        # await self.config.clear_all()
        my_categories = await self.config.categories()
        GLOBAL_CATEGORIES[:] = [Category(**i) for i in my_categories]

        # make the uncategorised cogs
        all_loaded_cogs = set(self.bot.cogs.keys())
        uncategorised = all_loaded_cogs - set(
            chain(*(category["cogs"] for category in my_categories))
        )

        uncat_config = await self.config.uncategorised()
        GLOBAL_CATEGORIES.append(
            Category(
                name=uncat_config["name"] if uncat_config["name"] else "uncategorised",
                desc=uncat_config["desc"]
                if uncat_config["desc"]
                else "No category commands",
                reaction=uncat_config["reaction"] if uncat_config["reaction"] else None,
                cogs=list(uncategorised),
            )
        )

    async def _setup(self):
        await self.refresh_cache()
        main_theme = BaguetteHelp(self.bot)
        theme = await self.config.theme()
        if all(theme.values()) == None:
            pass
        else:
            for feature in theme:
                if theme[feature]:
                    inherit_feature = getattr(
                        themes.list[theme[feature]], self.feature_list[feature]
                    )
                    setattr(
                        main_theme,
                        self.feature_list[feature],
                        MethodType(inherit_feature, main_theme),
                    )
        self.bot.set_help_formatter(main_theme)

    @checks.is_owner()
    @commands.group()
    async def chelp(self, ctx):
        """Configure your custom help"""

    @chelp.command(name="set")
    async def set_formatter(self, ctx, setval: bool):
        """Set to toggle custom formatter or the default help formatter \n `[p]chelp set 0` to turn custom off \n `[p]chelp set 1` to turn it on"""
        async with ctx.typing():
            try:
                if setval:
                    self.bot.set_help_formatter(BaguetteHelp(self.bot))
                    await ctx.send("Fomatter set to custom")
                else:
                    self.bot.reset_help_formatter()
                    await ctx.send("Resetting formatter to default")
            except RuntimeError as e:
                await ctx.send(str(e))
                return

    @chelp.command()
    async def create(self, ctx):
        """Create a new category to add cogs to it using yaml"""
        await ctx.send(
            "Your next message should be a yaml with the specfied format as in the docs"
        )
        msg = await self.bot.wait_for(
            "message",
            timeout=180,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
        )
        try:
            parsed_data = yaml.safe_load(msg.content)
        except yaml.parser.ParserError:
            await ctx.send("Wrongly formatted")
            return
        except yaml.scanner.ScannerError as e:
            await ctx.send(box(e))
            return

        if type(parsed_data) != dict:
            await ctx.send("Invalid Format")

        # TODO pls get a better type checking method
        for i in parsed_data:
            if type(parsed_data[i]) != list:
                await ctx.send("Invalid Format")
                return

        available_categories_raw = await self.config.categories()
        available_categories = [
            category["name"] for category in available_categories_raw
        ]
        all_cogs = set(self.bot.cogs.keys())
        uncategorised = all_cogs - set(
            chain(*(category["cogs"] for category in available_categories_raw))
        )
        failed_cogs = []
        success_cogs = []

        def parse_to_config(x):
            name = x
            cogs = []
            for cog_name in parsed_data[x]:
                if cog_name in uncategorised:
                    cogs.append(cog_name)
                    success_cogs.append(cog_name)
                    uncategorised.remove(cog_name)
                else:
                    failed_cogs.append(cog_name)
            return {"name": x, "desc": "Not provided", "cogs": cogs, "reaction": None}

        # TODO bunch the config calls
        for category in parsed_data:
            # check if category does not exist
            if category not in available_categories:
                async with self.config.categories() as conf_cat:
                    conf_cat.append(parse_to_config(category))
            else:
                # Else update the existing category
                async with self.config.categories() as conf_cat:
                    conf_cat[available_categories.index(category)]["cogs"].extend(
                        parse_to_config(category)["cogs"]
                    )

        for page in pagify(
            (
                f"Successfully loaded: `{'`,`'.join(success_cogs)}`"
                if success_cogs
                else "Nothing successful"
            )
            + (
                f"\n\nThe following cogs failed due to invalid or already present in a category: `{'`,`'.join(failed_cogs)}` "
                if failed_cogs
                else ""
            )
        ):
            await ctx.send(page)
        await self.refresh_cache()

    @chelp.command()
    async def removeall(self, ctx):
        """This will delete all the categories"""
        await ctx.send(
            "Warning: You are about to delete all your categories, type `y` else this is abort"
        )
        msg = await self.bot.wait_for(
            "message",
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
            timeout=60,
        )
        if msg.content == "y":
            await self.config.clear_all()
            self.config.register_global(**self.chelp_global)
            await ctx.send("Cleared all categories")
            await self.refresh_cache()
            return
        await ctx.send("Aborted")

    """
    @chelp.command()  # TODO
    async def removecog(self, ctx, category: str, cog: str):
        await ctx.send("WIP")
        
        await getattr(self.config.categories, category).clear()
        self.available_categories = await self.config.categories()
        await ctx.send(f"Removed {cog} from {category}")
    """

    @chelp.command()
    async def list(self, ctx):
        """Show the list of categories and the cogs in them"""
        available_categories_raw = await self.config.categories()
        available_categories = (
            category["name"] for category in available_categories_raw
        )
        all_cogs = set(self.bot.cogs.keys())
        uncategorised = all_cogs - set(
            chain(*(category["cogs"] for category in available_categories_raw))
        )
        joined = (
            _("Set Categories:\n")
            if len(available_categories_raw) > 1
            else _("Set Category:\n")
        )
        for category in available_categories_raw:
            joined += "+ {}\n".format(category["name"])
            for cog in category["cogs"]:
                joined += "  - {}\n".format(cog)
        joined += "\n+ {}\n".format("Uncategorised")
        for name in uncategorised:
            joined += "  - {}\n".format(name)
        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @chelp.group()
    async def add(self, ctx):
        """Add reactions and descriptions when needed"""

    # TODO merge desc and reaction cause they are copypasta same code
    @add.command(aliases=["descriptions", "description"])
    async def desc(self, ctx):
        """Add a Short description to your categories"""
        await ctx.send(
            "Your next message should be a yaml with \n category: description\n example:\nfun: fun commands\nmod: Moderations stuff"
        )
        msg = await self.bot.wait_for(
            "message",
            timeout=180,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
        )
        parsed_data = [cat for cat in msg.content.split("\n")]
        available_categories = [
            category["name"] for category in await self.config.categories()
        ]
        success = []
        # special naming for uncategorized stuff
        uncat_config = await self.config.uncategorised()
        uncat_config["name"] = (
            uncat_config["name"] if uncat_config["name"] else "uncategorised"
        )
        for i in range(len(parsed_data)):
            temp = parsed_data[i].split(":")
            if len(temp) != 2:
                pass
            else:
                # TODO bunch the config calls
                if uncat_config["name"] == temp[0]:
                    async with self.config.uncategorised() as unconf_cat:
                        unconf_cat["desc"] = temp[1].strip()
                    success.append(temp[0])
                    continue
                if temp[0] in available_categories:
                    async with self.config.categories() as conf_cat:
                        conf_cat[available_categories.index(temp[0])]["desc"] = temp[
                            1
                        ].strip()
                    success.append(temp[0])

        for page in pagify(
            f"Successfully added description to: `{'`,`'.join(success)}`"
            if success
            else "Nothing successful"
        ):
            await ctx.send(page)
        await self.refresh_cache()

    @add.command(aliases=["reactions"])
    async def reaction(self, ctx):
        """Add reactions to redirect to your category"""
        await ctx.send(
            "Your next message should be a yaml with \n category: reaction\n"
            "Reactions **must** be default ones not from a server \n"
            "You can't have 2 categories with the same reaction \n"
            "example:\nfun: \N{SMILING FACE WITH OPEN MOUTH AND SMILING EYES}\nmod: \N{SHIELD}\N{VARIATION SELECTOR-16}"
        )
        msg = await self.bot.wait_for(
            "message",
            timeout=180,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
        )
        parsed_data = [cat for cat in msg.content.split("\n")]
        available_categories = [
            category["name"] for category in await self.config.categories()
        ]
        success = []
        uncat_config = await self.config.uncategorised()
        uncat_config["name"] = (
            uncat_config["name"] if uncat_config["name"] else "uncategorised"
        )
        for i in range(len(parsed_data)):
            temp = parsed_data[i].split(":")
            temp[1] = temp[1].strip()[0]
            if len(temp) != 2:
                pass
            else:
                already_present_emojis = (i.reaction for i in GLOBAL_CATEGORIES)
                if temp[1] not in already_present_emojis:
                    # valid emoji?
                    if temp[1] in UNICODE_EMOJI:
                        # special uncategorised
                        if uncat_config["name"] == temp[0]:
                            async with self.config.uncategorised() as unconf_cat:
                                unconf_cat["reaction"] = temp[1]
                            success.append(temp[0])
                            continue
                        # valid category?
                        if temp[0] in available_categories:
                            # TODO bunch the config calls
                            async with self.config.categories() as conf_cat:
                                conf_cat[available_categories.index(temp[0])][
                                    "reaction"
                                ] = temp[1]
                            success.append(temp[0])

        for page in pagify(
            f"Successfully added description to: `{'`,`'.join(success)}`"
            if success
            else "Nothing successful"
        ):
            await ctx.send(page)
        await self.refresh_cache()

    @chelp.command()
    async def load(self, ctx, theme: str, feature: str):
        """Load another preset theme"""
        if theme in themes.list:
            if feature in self.feature_list:
                inherit_theme = themes.list[theme]
                if hasattr(inherit_theme, self.feature_list[feature]):
                    inherit_feature = getattr(
                        themes.list[theme], self.feature_list[feature]
                    )
                    # load up the attribute,Monkey patch me daddy UwU
                    setattr(
                        self.bot._help_formatter,
                        self.feature_list[feature],
                        MethodType(inherit_feature, self.bot._help_formatter),
                    )
                else:
                    await ctx.send(f"{theme} doesn't have the feature {feature}")

                # update config
                await getattr(self.config.theme, feature).set(theme)
                await ctx.tick()
            else:
                await ctx.send("Feature not found")
        else:
            await ctx.send("Theme not found")

    @chelp.command()
    async def reset(self, ctx):
        """Resets all settings to default **custom** help \n use `[p]chelp set 0` to revert back to the old help"""
        # TODO add a prompt here
        self.bot.reset_help_formatter()
        self.bot.set_help_formatter(BaguetteHelp(self.bot))
        await self.config.theme.set(
            {"cog": None, "category": None, "command": None, "main": None}
        )
        await ctx.tick()

    @chelp.command()
    async def unload(self, ctx, feature: str):
        """Unloads the given feature, this will reset to default"""
        if feature in self.feature_list:
            setattr(
                self.bot._help_formatter,
                self.feature_list[feature],
                MethodType(
                    getattr(BaguetteHelp, self.feature_list[feature]),
                    self.bot._help_formatter,
                ),
            )
        else:
            await ctx.send(f"Invalid feature: {feature}")
            return
        # update config
        await getattr(self.config.theme, feature).set(None)
        await ctx.tick()

    @chelp.command()
    async def settings(self, ctx):
        """Display the current settings"""
        val = await self.config.theme()
        val = "\n".join(
            [f"`{i:<10}`: " + (j if j else "default") for i, j in val.items()]
        )
        emb = discord.Embed(title="Custom help settings")
        emb.add_field(name="Theme", value=val)
        await ctx.send(embed=emb)

    @chelp.command()
    async def listthemes(self, ctx):
        """List the themes and available features"""
        outs = {i: [] for i in themes.list}
        for x in themes.list:
            for y in self.feature_list:
                if self.feature_list[y] in themes.list[x].__dict__:
                    outs[x].append((y, "✅"))
                else:
                    outs[x].append((y, "❎"))
        final = tabulate(
            [list(chain([i], *[x[1] for x in j])) for i, j in outs.items()],
            headers=["#"] + list(self.feature_list.keys()),
            tablefmt="presto",
            stralign="center",
        )

        await ctx.send(box(final))

    @chelp.command()
    async def uncategory(self, ctx, thing: str, *, item):
        """This is to change the name,description and reaction of uncategorised cogs.
        you can change the name,desc and reaction
        example:\n[p]chelp uncategory name notcategorized\n[p]chelp uncategory desc weird cogs\n[p]chelp uncategory reaction \U0001f604"""
        change = ["name", "desc", "reaction"]
        if thing in change:
            async with self.config.uncategorised() as un_conf:
                un_conf[thing] = item
        await self.refresh_cache()

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
