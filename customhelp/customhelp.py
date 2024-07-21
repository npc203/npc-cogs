# pyright: reportGeneralTypeIssues=false
import asyncio
import json
import re
from collections import Counter, defaultdict
from inspect import getfile
from itertools import chain
from os import path
from pathlib import Path
from types import MethodType
from typing import Dict, List, Optional

import discord
import yaml
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import menus, predicates
from redbot.core.utils.chat_formatting import box, pagify
from tabulate import tabulate

from . import themes
from .core import ARROWS, GLOBAL_CATEGORIES
from .core.base_help import EMPTY_STRING, BaguetteHelp
from .core.category import Arrow, Category, get_category
from .core.utils import LINK_REGEX, emoji_converter
from .core.views import ComponentType, MenuPicker, MenuView

_ = Translator("CustomHelp", __file__)

# Switchable alphabetic ordered display
# Crowdin stuff ;-;
# Generating every category page on format_bot_help so as to save time in reaction stuff?
# No need to fetch config uncat, when u can use global cache, but is that better?
# TODO is rewriting everything to use global cache instead of config, better?
# TODO Need to remove tons of redundant code in themes
"""
Config Structure:
    {
      "categories":
      [
            {
                "name" : name
                "desc" : desc
                "long_desc":longer description
                "cogs" : []
                "reaction":None
                "label":""
                "style":"primary"
                "is_uncat": False
            }
     ]
    }
"""


@cog_i18n(_)
class CustomHelp(commands.Cog):
    """
    A custom customisable help for fun and profit
    """

    __version__ = "1.1.0"

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
            "version": "0.0.0",
            "categories": [],
            "theme": {"cog": None, "category": None, "command": None, "main": None},
            "settings": {
                "nav": True,
                "set_formatter": False,
                "thumbnail": None,
                "timeout": 120,
                "replies": True,
                "menutype": "buttons",  # "emojis","buttons","select","hidden"
                "arrowtype": "buttons",  # "emojis","buttons","select","hidden"
                "deletemessage": False,
            },
            "arrows": [
                {"name": "force_left", "emoji": "⏮️", "style": "primary", "label": ""},
                {"name": "left", "emoji": "⬅️", "style": "primary", "label": ""},
                {"name": "cross", "emoji": "❌", "style": "primary", "label": ""},
                {"name": "right", "emoji": "➡️", "style": "primary", "label": ""},
                {"name": "force_right", "emoji": "⏭️", "style": "primary", "label": ""},
                {"name": "home", "emoji": "🏘️", "style": "primary", "label": ""},
            ],
            "blacklist": {"nsfw": [], "dev": []},
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

    async def refresh_arrows(self):
        """This is to make the emoji arrows objects be in their proper types"""
        arrows = await self.config.arrows()
        ARROWS.clear()
        for index, details in enumerate(arrows):
            details["style"] = getattr(discord.ButtonStyle, details["style"])
            if emj := emoji_converter(self.bot, details.pop("emoji")):
                ARROWS.append(Arrow(**details, emoji=emj))
            else:
                # back-up measure if the something went wrong
                print(
                    "Warning CustomHelp: emoji coverter failed for arrow",
                    self.chelp_global["settings"]["arrows"][index]["name"],
                )
                ARROWS.append(
                    Arrow(**details, emoji=self.chelp_global["settings"]["arrows"][index]["emoji"])
                )

    async def refresh_cache(self):
        """Get's the config and re-populates the GLOBAL_CATEGORIES"""
        # Just in case if there's no uncategorised category
        await self.add_placeholder_uncategorised()

        # Blocking?
        my_categories = await self.config.categories()
        GLOBAL_CATEGORIES.clear()
        for cat_data in my_categories:
            cat_obj = Category(**cat_data)
            # Correct the emoji types
            cat_obj.reaction = emoji_converter(self.bot, cat_obj.reaction)
            GLOBAL_CATEGORIES.append(cat_obj)

        # make the uncategorised cogs
        all_loaded_cogs = set(self.bot.cogs.keys())
        uncategorised = all_loaded_cogs - set(
            chain(*(category["cogs"] for category in my_categories))
        )

        GLOBAL_CATEGORIES.uncategorised.cogs = list(uncategorised)

    async def add_placeholder_uncategorised(self):
        # Make sure there's no is_uncat category
        for cat in await self.config.categories():
            if cat.get("is_uncat", False) == True:
                break
        else:
            # Create uncat category
            # Doesn't work cause force_registration=True
            # uncat_conf = await self.config.uncategorised()
            uncat_obj = Category(
                name="uncategorised‎", desc="Miscellaneous cogs", cogs=[], is_uncat=True
            )
            async with self.config.categories() as conf_cat:
                conf_cat.append(uncat_obj.to_dict())

    async def cog_load(self):
        """Adds the themes and loads the formatter"""

        # Arrow migration
        if (await self.config.version()) < "1.0.0":
            new_arrows = []
            try:
                async with self.config.settings.arrows() as arrows:
                    for name, emoji in arrows.items():
                        new_arrows.append(
                            {"name": name, "emoji": emoji, "style": "primary", "label": ""}
                        )
                    arrows.clear()
                await self.config.arrows.set(new_arrows)
            except AttributeError:
                # We don't care if settings.arrows doesn't exist in the first place
                pass
            await self.config.version.set(self.__version__)

        # Category migration V1 - not needed anymore
        # if (await self.config.version()) < "1.0.1":
        #     async with self.config.uncategorised() as uncat:
        #         uncat["style"] = "primary"
        #         uncat["label"] = ""
        #     await self.config.version.set(self.__version__)

        # Category migration V2 - add uncategorised to categories in config
        # Probably redundant
        # if (await self.config.version()) < "1.1.0":
        #     await self.add_placeholder_uncategorised()
        #     await self.config.version.set(self.__version__)

        # This is needed to be on top so that Cache gets populated no matter what (supplements chelp create)
        await self.refresh_cache()
        await self.refresh_arrows()

        settings = await self.config.settings()
        if not settings["set_formatter"]:
            return

        # Setup the formatter
        main_theme = BaguetteHelp(
            self.bot, await self.config.settings(), await self.config.blacklist()
        )
        theme = await self.config.theme()
        if all(theme.values()) is not None:
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

    @commands.Cog.listener("on_cog_add")
    async def handle_new_cog_entries(self, cog: commands.Cog):
        cog_name = cog.__class__.__name__
        # GLOBAL_CATEGORIES should be populated by now, cause cog_load is called before this
        for cat in GLOBAL_CATEGORIES:
            if cog_name in cat.cogs:
                break
        else:
            GLOBAL_CATEGORIES.uncategorised.cogs.append(cog_name)

    # TODO implement!, careful, people do reload cogs
    # @commands.Cog.listener("on_cog_remove")
    # async def handle_cog_remove(self, cog: commands.Cog):
    #     # cog_name = cog.__class__.__name__
    #     pass

    @commands.is_owner()
    @commands.group()
    async def chelp(self, ctx):
        """Configure your custom help"""

    @chelp.command()
    async def info(self, ctx):
        """Short info about various themes"""
        emb = discord.Embed(color=await ctx.embed_color(), title="All Themes")
        for theme in themes.list:
            emb.add_field(name=theme, value=themes.list[theme].__doc__, inline=False)
        await ctx.send(embed=emb)

    @chelp.command()
    async def refresh(self, ctx):
        """Force refresh the list of categories, This would reset all the uninstalled/unloaded cogs and will put them into uncategorised."""
        all_cogs = set(self.bot.cogs.keys())

        async with self.config.categories() as my_categories:
            for category in my_categories:
                if category.get("is_uncat"):
                    continue
                category["cogs"][:] = [cog for cog in category["cogs"] if cog in all_cogs]

        await self.refresh_cache()
        await ctx.tick()

    @chelp.command()
    async def auto(self, ctx):
        """Auto categorise cogs based on it's tags and display them"""
        data: Dict[str, List[str]] = {}
        # Thanks trusty pathlib is awesome.
        for k, a in self.bot.cogs.items():
            check = Path(getfile(a.__class__)).parent / "info.json"
            if path.isfile(check):
                with open(check, "r", encoding="utf-8") as f:
                    try:
                        tmp = json.load(f)
                        data[k] = [i.lower() for i in tmp["tags"]] if "tags" in tmp else []
                    except json.JSONDecodeError:
                        # TODO Implement logger you lazy bum <_<
                        print(f"[ERROR] Invalid JSON in cog {k}")
                        data[k] = []

            else:
                data[k] = []

        # Ofc grouping was done with the help random ppl helping me in pydis guild+stackoverflow :aha:
        popular = Counter(chain.from_iterable(data.values()))
        groups = defaultdict(set)
        for key, tags in data.items():
            if tags:
                tag = max(
                    tags,
                    key=popular.get,  # type:ignore https://github.com/microsoft/pylance-release/issues/1022
                )
                groups[tag].add(key)

        final = {"uncategorised": []}
        for i, j in groups.items():
            if len(j) > 1:
                final[i] = list(j)
            else:
                final["uncategorised"].extend(j)
        for i in [
            box(page, lang="yaml")
            for page in pagify(yaml.dump(final), shorten_by=0, page_length=1990)
        ]:
            await ctx.send(i)

    @chelp.command()
    async def show(self, ctx):
        """Show the current help settings"""
        settings = await self.config.settings()
        blocklist = await self.config.blacklist()
        setting_mapping = {
            "set_formatter": "iscustomhelp?",
            "thumbnail": "thumbnail",
            "menus": "Menu-Type",
            "replies": "Use replies",
            "react": "React",
            "menutype": "MenuType",
            "arrowtype": "ArrowType",
            "timeout": "Timeout",
            "deletemessage": "Delete user msg",
        }
        other_settings = []
        # url doesnt exist now, that's why the check. sorry guys.
        for i, j in settings.items():
            if i in setting_mapping:
                other_settings.append(f"`{setting_mapping[i]:<15}`: {j}")
        val = await self.config.theme()
        val = "\n".join([f"`{i:<10}`: " + (j if j else "default") for i, j in val.items()])
        emb = discord.Embed(
            title="Custom help settings",
            description=f"Cog Version: {self.__version__}",
            color=await ctx.embed_color(),
        )
        emb.add_field(name="Theme", value=val)
        emb.add_field(
            name="Other Settings",
            value="\n".join(other_settings),
            inline=False,
        )

        # TODO PAGINATE TO DISPLAY
        # emb.add_field(
        #     name="Arrows",
        #     value="\n".join(f"`{i:<7}`: {j}" for i, j in ARROWS.items()),
        #     inline=False,
        # )

        if blocklist["nsfw"] or blocklist["dev"]:
            emb.add_field(
                name=EMPTY_STRING,
                value="".join(
                    f"**{i.capitalize()} categories:**\n{', '.join(blocklist[i])}\n"
                    for i in blocklist
                    if blocklist[i]
                )
                or EMPTY_STRING,
                inline=False,
            )
        await ctx.send(embed=emb)

    @chelp.command(name="toggle")
    async def set_formatter(self, ctx, setval: bool):
        """Set to toggle custom formatter or the default help formatter\n`[p]chelp toggle 0` to turn custom off \n`[p]chelp toggle 1` to turn it on"""
        async with ctx.typing():
            try:
                if setval:
                    # TODO potential save a config call?
                    await self.config.settings.set_formatter.set(True)
                    await self.cog_load()
                    await ctx.send("Formatter set to custom")
                else:
                    await self.config.settings.set_formatter.set(False)
                    self.bot.reset_help_formatter()
                    await ctx.send("Resetting formatter to default")
            except RuntimeError as e:
                await ctx.send(str(e))

    @chelp.command(aliases=["add"])
    async def create(self, ctx, *, yaml_txt=None):
        """Create a new category to add cogs to it using yaml"""
        if yaml_txt:
            content = yaml_txt
        else:
            await ctx.send(
                "Your next message should be a yaml with the specified format as in the docs\n"
                "Example:\n"
                "category1:\n"
                " - Cog1\n - Cog2"
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

        parsed_data = await self.parse_yaml(ctx, content)
        if not parsed_data:
            return

        # counter part of edit's yaml bug report fix
        for i in parsed_data.values():
            if any(type(j) != str for j in i):
                await ctx.send("Invalid Format, Likely you added an extra ':' or '-'")
                return

        available_categories = [
            category.name for category in GLOBAL_CATEGORIES if category.is_uncat == False
        ]
        # Not using cache (GLOBAL_CATEGORIES.uncategorised.cogs) cause cog unloads aren't tracked
        all_cogs = set(self.bot.cogs.keys())
        uncategorised = all_cogs - set(
            chain(
                *(
                    GLOBAL_CATEGORIES.get(category_name).cogs
                    for category_name in available_categories
                )
            )
        )

        uncat_name = GLOBAL_CATEGORIES.uncategorised.name
        failed_cogs = []
        success_cogs = []

        def parse_to_config(x: str):
            cogs = []
            for cog_name in parsed_data[x]:
                if cog_name in uncategorised:
                    cogs.append(cog_name)
                    success_cogs.append(cog_name)
                    uncategorised.remove(cog_name)
                else:
                    failed_cogs.append(cog_name)
            return {"name": x, "desc": "Not provided", "cogs": cogs, "reaction": None}

        # {"new": [{cat_conf_structure,...}, {...}] , "existing": { category_name: [cogs], ..}}
        to_config = {"new": [], "existing": defaultdict(list)}
        for category in parsed_data:
            if uncat_name == category or " " in category:
                failed_cogs.append(category)
                continue
            # check if category exist
            if category in available_categories:
                # update the existing category
                to_config["existing"][category].extend(parse_to_config(category)["cogs"])
            else:
                to_config["new"].append(parse_to_config(category))

        # Writing to config
        async with self.config.categories() as conf_cat:
            conf_cat.extend(to_config["new"])
            for category_name, cat_conf in to_config["existing"].items():
                for config_category in conf_cat:
                    if config_category["name"] == category_name:
                        config_category["cogs"].extend(cat_conf)

        for page in pagify(
            (
                f"Successfully loaded: `{'`,`'.join(success_cogs)}`"
                if success_cogs
                else "Nothing successful"
            )
            + (
                f"\n\nThe following categorie(s)/cog(s) failed due to invalid name or already present in a category: `{'`,`'.join(failed_cogs)}` "
                if failed_cogs
                else ""
            )
        ):
            await ctx.send(page)
        await self.refresh_cache()

    @chelp.command()
    async def edit(self, ctx, *, yaml_txt=None):
        """Add reactions and descriptions to the category"""
        if yaml_txt:
            content = yaml_txt
        else:
            await ctx.send(
                "Your next message should be a yaml with the specfied format as in the docs\n"
                "Example:\n"
                "category1:\n"
                " - name: newname(use this ONLY for renaming)\n"
                " - reaction: \U0001f604\n"
                " - desc: short description\n"
                " - long_desc: long description (Optional,only displayed in dank theme)\n"
                " - thumbnail: url to thumbnail for the category\n"
                " - label: Label for category (For category and buttons)\n"
                " - style: ButtonStyle for category button\n (primary, secondary, success, danger)"
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

        parsed_data = await self.parse_yaml(ctx, content)
        if not parsed_data:
            return
        # twin's bug report fix
        for i in parsed_data.values():
            if any(type(j) == str for j in i):
                await ctx.send("Invalid Format, Likely you added an extra ':' or '-'")
                return
        # Some more rearrangement parsed_data = {category:[('name', 'notrandom'), ('emoji', 'asds'), ('emoji', '😓'), ('desc', 'this iasdiuasd')]}
        parsed_data = {
            i: [(k, v) for f in my_list for k, v in f.items()]
            for i, my_list in parsed_data.items()
        }
        check = ["name", "desc", "long_desc", "reaction", "thumbnail", "label", "style"]
        available_categories = [
            category.name for category in GLOBAL_CATEGORIES if category.is_uncat == False
        ]
        already_present_emojis = [str(i.reaction) for i in GLOBAL_CATEGORIES if i.reaction] + [
            i.emoji for i in ARROWS
        ]
        failed = []  # example: [('desc','categoryname')]

        def validity_checker(category, item):
            """Returns the thing needs to be saved on config if valid, else None"""
            if item[0] in check:
                if item[0] == "name":
                    if " " not in item[1] and item[1] not in available_categories:
                        return item[1]
                # dupe emoji and valid emoji?
                elif item[0] == "reaction":
                    if item[1] not in already_present_emojis:
                        return str(emoji_converter(self.bot, item[1]))
                elif item[0] == "style":
                    return item[1] if hasattr(discord.ButtonStyle, item[1]) else None
                else:
                    return item[1]

        # format: {category_name:[(name,value),..],..} --- could use defaultdict(list)
        to_config = {}
        uncat_name = GLOBAL_CATEGORIES.uncategorised.name
        for category_name in parsed_data:
            # default uncat name is "uncategorised‎"
            if (
                category_name in available_categories
                or category_name == uncat_name
                or (category_name == "uncategorised" and uncat_name == "uncategorised‎")
            ):
                to_config[category_name] = {}

                for item in parsed_data[category_name]:
                    if tmp_value := validity_checker(category_name, item):
                        to_config[category_name][item[0]] = tmp_value
                    else:
                        failed.append((item, category_name))
            else:
                # TODO make this a lil neater for Everything failed?
                failed.append((("[Not a valid category name]", "Everything"), category_name))

        if to_config:
            async with self.config.categories() as conf_cat:
                for category_name in to_config.keys():
                    for category_config in conf_cat:
                        if category_config["name"] == category_name:
                            category_config.update(to_config[category_name])

        for page in pagify(
            "Successfully added the edits"
            if not failed
            else "The following things failed:\n"
            + "\n".join(
                [
                    f"`{reason[0]}`: {reason[1]}  failed in `{category}`"
                    for reason, category in failed
                ]
            )
        ):
            await ctx.send(page)
        await self.refresh_cache()

    # Taken from api listing from core
    @chelp.command()
    async def list(self, ctx):
        """Show the list of categories and the cogs in them"""
        # TODO maybe its a better option to read from cache than config?
        available_categories_raw = await self.config.categories()
        all_cogs = set(self.bot.cogs.keys())
        uncategorised = all_cogs - set(
            chain(*(category["cogs"] for category in available_categories_raw))
        )
        joined = (
            _("Set Categories:\n") if len(available_categories_raw) > 1 else _("Set Category:\n")
        )
        for category in available_categories_raw:
            if category.get("is_uncat") == True:
                joined += "+ {} (This is where the uncategorised cogs go in):\n".format(
                    category["name"]
                )
                for cog in sorted(uncategorised):
                    joined += "  - {}\n".format(cog)
            else:
                joined += "+ {}:\n".format(category["name"])
                for cog in sorted(category["cogs"]):
                    joined += "  - {}\n".format(cog)

        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @chelp.command()
    async def load(self, ctx, theme: str, feature: str):
        """Load another preset theme.\nUse `[p]chelp load <theme> all` to load everything from that theme"""

        if type(self.bot._help_formatter) is commands.help.RedHelpFormatter:
            await ctx.send("You are not using the custom formatter")
            return

        def loader(theme, feature):
            inherit_theme = themes.list[theme]
            if hasattr(inherit_theme, self.feature_list[feature]):
                inherit_feature = getattr(themes.list[theme], self.feature_list[feature])
                # load up the attribute,Monkey patch me daddy UwU
                setattr(
                    self.bot._help_formatter,
                    self.feature_list[feature],
                    MethodType(inherit_feature, self.bot._help_formatter),
                )
                return True
            return False

        if theme in themes.list:
            if feature == "all":
                for i in self.feature_list:
                    if loader(theme, i):
                        await getattr(self.config.theme, i).set(theme)
                await ctx.tick()
            elif feature in self.feature_list:
                if loader(theme, feature):
                    await ctx.send(f"Successfully loaded {feature} from {theme}")
                    # update config
                    await getattr(self.config.theme, feature).set(theme)
                else:
                    await ctx.send(f"{theme} doesn't have the feature {feature}")
            else:
                await ctx.send("Feature not found")
        else:
            await ctx.send("Theme not found")

    @chelp.group(invoke_without_command=True)
    async def reset(self, ctx):
        """Resets all settings to default **custom** help \n use `[p]chelp set 0` to revert back to the old help"""
        msg = await ctx.send("Are you sure? This will reset everything back to the default theme.")
        menus.start_adding_reactions(msg, predicates.ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = predicates.ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            self.bot.reset_help_formatter()
            self.bot.set_help_formatter(
                BaguetteHelp(self.bot, await self.config.settings(), await self.config.blacklist())
            )
            await self.config.theme.set(
                {"cog": None, "category": None, "command": None, "main": None}
            )
            await self.refresh_cache()
            await ctx.send("Reset successful")
        else:
            await ctx.send("Aborted")

    @reset.command(hidden=True)
    async def hard(self, ctx):
        """Hard reset, clear everything"""
        await ctx.send(
            "Warning: You are about to delete EVERYTHING!, type `y` to continue else this will abort"
        )
        try:
            msg = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60,
            )
        except asyncio.TimeoutError:
            return await ctx.send("Timed out, please try again.")
        if msg.content == "y":
            # TODO there must be a better method in getting the defaults. remember?
            await self.config.clear_all()
            self.config.register_global(**self.chelp_global)
            self.bot.reset_help_formatter()
            await self._setup()
            await ctx.send("Cleared everything.")
        else:
            await ctx.send("Aborted")

    @chelp.command()
    async def unload(self, ctx, feature: str):
        """Unloads the given feature, this will reset to default"""
        if type(self.bot._help_formatter) is commands.help.RedHelpFormatter:
            await ctx.send("You are not using the custom formatter")
            return
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

    @chelp.group()
    async def remove(self, ctx):
        """Remove categories/cogs or everything"""

    @remove.command()
    async def all(self, ctx):
        """This will delete all the categories"""
        # NO i won't use the MessagePredicate, no bully ;-;
        await ctx.send(
            "Warning: You are about to delete all your categories, type `y` to continue else this will abort"
        )
        try:
            msg = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60,
            )
        except asyncio.TimeoutError:
            return await ctx.send("Timed out, please try again.")
        if msg.content == "y":
            # TODO there must be a better method in getting the defaults. remember?
            await self.config.categories.clear()
            await ctx.send("Cleared all categories")
            await self.refresh_cache()
            return
        await ctx.send("Aborted")

    @remove.command(aliases=["categories", "cat"], require_var_positional=True)
    async def category(self, ctx, *categories: str):
        """Remove a multiple categories"""
        category_names = set(map(lambda cat: cat.rstrip(","), categories))

        to_config = []
        invalid = []
        text = ""
        for given_category in category_names:
            for category in GLOBAL_CATEGORIES:
                if given_category == category.name and category.is_uncat == False:
                    to_config.append(category.name)
                    break
            else:
                # Uncategorised Name
                if given_category == GLOBAL_CATEGORIES.uncategorised.name or (
                    given_category == "uncategorised"
                    and GLOBAL_CATEGORIES.uncategorised.name == "uncategorised‎"
                ):
                    text += _(
                        "You can't remove {} cause it is where the uncategorised cogs go into\n\n"
                    ).format(given_category)
                else:
                    invalid.append(given_category)

        async with self.config.categories() as conf_cat:
            new_conf_list = []
            for cat in conf_cat:
                if cat["name"] not in to_config:
                    new_conf_list.append(cat)
            conf_cat[:] = new_conf_list

        text += _("Successfully removed: ") + (", ".join(to_config) + "\n") if to_config else ""
        if invalid:
            text += _("These categories aren't present in the list:\n" + ",".join(invalid))
        await self.refresh_cache()
        await ctx.send(text)

    @remove.command(aliases=["cogs"], require_var_positional=True)
    async def cog(self, ctx, *cog_raw_names: str):
        """Remove a cog(s) from across categories"""
        # From Core [p]load xD, using set to avoid dupes
        cog_names: set[str] = set(map(lambda cog: cog.rstrip(","), cog_raw_names))

        to_config = []  # [(category_name,cog_name),()] (maybe use namedtuples here?)
        uncat = []
        invalid = []

        def category_from_cog(cog_name):
            for category in GLOBAL_CATEGORIES:
                if cog_name in category.cogs:
                    return category.name
            return None

        uncat_name = GLOBAL_CATEGORIES.uncategorised.name
        for cog_name in cog_names:
            # valid cog
            if self.bot.get_cog(cog_name):
                cat_name = category_from_cog(cog_name)
                # cog is present in a category
                if cat_name is not None:
                    if cat_name == uncat_name:
                        uncat.append(cog_name)
                    else:
                        to_config.append((cat_name, cog_name))
                else:
                    # This is a rare case to occur, basically "cog is loaded and valid but it didn't get registered in the GLOBAL_CATEGORIES cache"
                    # Never came to this point, but having it as a check
                    await ctx.send(
                        f"Something errored out, kindly report to the owner of customhelp, \ncog name:{cog_name}"
                    )
            else:
                invalid.append(cog_name)
        async with self.config.categories() as cat_conf:
            for cat_name, cog_name in to_config:
                for category in cat_conf:
                    if cat_name == category["name"]:
                        category["cogs"].remove(cog_name)
                        break
        text = ""
        if to_config:
            text = "Successfully removed the following\n"
            last = None
            for thing in sorted(to_config, key=lambda x: x[0]):
                if last == thing[0]:
                    text += " - {}\n".format(thing[1])
                else:
                    text += _("From {}:\n - {}\n").format(thing[0], thing[1])
                    last = thing[0]
        if uncat:
            text += (
                "The following cogs are present in 'uncategorised' and cannot be removed:\n"
                + (", ".join(uncat))
            )
        if invalid:
            text += "The following cogs are invalid or unloaded:\n" + (", ".join(invalid))

        await self.refresh_cache()
        for page in pagify(text, page_length=1985, shorten_by=0):
            await ctx.send(box(page, lang="yaml"))

    @chelp.group(name="set", aliases=["settings", "setting"])
    async def chelp_settings(self, ctx):
        """Change various help settings"""

    @chelp_settings.command(name="type")
    async def type_(self, ctx):
        """Toggles between various menus and arrow types"""
        options = [
            discord.SelectOption(
                label="Emojis", description="Old-Fashion, Highly ratelimited", emoji="😃"
            ),
            discord.SelectOption(label="Buttons", description="Cool chonky buttons", emoji="🟦"),
            discord.SelectOption(
                label="Select", description="Minimalistic Dropdown Menus", emoji="⏬"
            ),
            discord.SelectOption(
                label="Hidden", description="No components are shown", emoji="🥷"
            ),
        ]
        select_bar_view = MenuView(ctx.author.id, self.config.settings, self._update_conf)
        select_bar_view.add_item(MenuPicker(ComponentType.MENU, options))
        select_bar_view.add_item(MenuPicker(ComponentType.ARROW, options))

        select_bar_view.message = await ctx.send(
            "Pick your options from the list shown", view=select_bar_view
        )

    @chelp_settings.command(aliases=["setthumbnail"])
    async def thumbnail(self, ctx, url: Optional[str] = None):
        """Set your main thumbnail image here.\n use `[p]chelp settings thumbnail` to reset this"""
        if url:
            if re.search(LINK_REGEX, url):
                await self.config.settings.thumbnail.set(url)
                self._update_conf("settings", "thumbnail", url)
                await ctx.tick()
            else:
                await ctx.send("Enter a valid url")
        else:
            await self.config.settings.thumbnail.set(None)
            self._update_conf("settings", "thumbnail", None)
            await ctx.send("Reset thumbnail")

    @chelp_settings.command(aliases=["usereplies", "reply"])
    async def usereply(self, ctx, option: bool):
        """Enable/Disable replies"""
        await self.config.settings.replies.set(option)
        self._update_conf("settings", "replies", option)
        await ctx.send(f"{'Enabled' if option else 'Disabled'} reply menus")

    @chelp_settings.command()
    async def nav(self, ctx, option: bool):
        """Enable/Disable navigation arrows
        Disabling this removes every trace of arrows and you can't move to the next page
        People wanted this for some reason lol"""
        await self.config.settings.nav.set(option)
        self._update_conf("settings", "nav", option)
        await ctx.send(f"{'Enabled' if option else 'Disabled'} navigation arrows")

    @chelp_settings.command()
    async def timeout(self, ctx, wait: int):
        """Set how long the help menu must stay active"""
        if wait > 20:
            await self.config.settings.timeout.set(wait)
            self._update_conf("settings", "timeout", wait)
            await ctx.send(f"Successfully set timeout to {wait}")
        else:
            await ctx.send("Timeout must be atleast 20 seconds")

    @chelp_settings.command(aliases=["deleteusermessage"])
    async def deletemessage(self, ctx, toggle: bool):
        """Delete the user message that started the help menu.
        Note: This only works if the bot has permissions to delete the user message, otherwise it's supressed
        """
        await self.config.settings.deletemessage.set(toggle)
        self._update_conf("settings", "deletemessage", toggle)
        await ctx.send(f"Successfully set delete user toggle to {toggle}")

    @chelp_settings.command(aliases=["arrow"])
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
                " - style: success\n (primary, secondary, success, danger)"
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

        if not (yaml_data := await self.parse_yaml(ctx, content)):
            return

        already_present_emojis = list(str(i.reaction) for i in GLOBAL_CATEGORIES if i.reaction) + [
            i["emoji"] for i in await self.config.arrows()
        ]

        parsed = {}
        failed = []  # [(reason for failure,arrow_name)]
        check = ("emoji", "label", "style")
        check_name = ("left", "right", "cross", "home", "force_right", "force_left")
        check_style = ["primary", "secondary", "success", "danger"]

        parsed_data = {}
        for k, v in yaml_data.items():
            tmp = {}
            for val in v:
                # Scuffed checking for bad yaml parse
                if not isinstance(val, dict):
                    return await ctx.send(
                        "Invalid syntax, kindly follow the yaml syntax given in the docs"
                    )
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
                    if emoji in already_present_emojis:
                        failed.append((("emoji", "Emoji already present as arrow"), arrow))
                    elif converted := emoji_converter(self.bot, emoji):
                        parsed[arrow]["emoji"] = converted

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

    @chelp.group()
    async def nsfw(self, ctx):
        """Add categories to nsfw, only displayed in nsfw channels"""

    @nsfw.command(name="add")
    async def add_nsfw(self, ctx, category: str):
        """Add categories to the nsfw list"""
        if cat_obj := get_category(category):
            if "Core" in cat_obj.cogs:
                return await ctx.send(
                    "This category contains Core cog and shouldn't be hidden under any circumstances"
                )
            else:
                async with self.config.blacklist.nsfw() as conf:
                    if category not in conf:
                        conf.append(category)
                        self._update_conf("blacklist_names", "nsfw", conf)
                        await ctx.send(f"Successfully added {category} to nsfw category")
                    else:
                        await ctx.send(f"{category} is already present in nsfw blocklist")
        else:
            await ctx.send("Invalid category name")

    @nsfw.command(name="remove")
    async def remove_nsfw(self, ctx, category: str):
        """Remove categories from the nsfw list"""
        cat_obj = get_category(category) or (
            category if category in await self.config.blacklist.nsfw() else None
        )
        if cat_obj:
            async with self.config.blacklist.nsfw() as conf:
                if category in conf:
                    conf.remove(category)
                    self._update_conf("blacklist_names", "nsfw", conf)
                    await ctx.send(f"Successfully removed {category} from nsfw category")
                else:
                    await ctx.send(f"{category} is not present in nsfw blocklist")
        else:
            await ctx.send("Invalid category name")

    @chelp.group()
    async def dev(self, ctx):
        """Add categories to dev, only displayed to the bot owner(s)"""

    @dev.command(name="add")
    async def add_dev(self, ctx, category: str):
        """Add categories to the dev list"""
        if cat_obj := get_category(category):
            if "Core" in cat_obj.cogs:
                return await ctx.send(
                    "This category contains Core cog and shouldn't be hidden under any circumstances"
                )
            else:
                async with self.config.blacklist.dev() as conf:
                    if category not in conf:
                        conf.append(category)
                        self._update_conf("blacklist_names", "dev", conf)
                        await ctx.send(f"Successfully added {category} to dev list")
                    else:
                        await ctx.send(f"{category} is already present in dev list")
        else:
            await ctx.send("Invalid category name")

    @dev.command(name="remove")
    async def remove_dev(self, ctx, category: str):
        """Remove categories from the dev list"""
        cat_obj = get_category(category) or (
            category if category in await self.config.blacklist.dev() else None
        )
        if cat_obj:
            async with self.config.blacklist.dev() as conf:
                if category in conf:
                    conf.remove(category)
                    self._update_conf("blacklist_names", "dev", conf)
                    await ctx.send(f"Successfully removed {category} from dev category")
                else:
                    await ctx.send(f"{category} is not present in dev list")
        else:
            await ctx.send("Invalid category name")

    @chelp.command(aliases=["getthemes"])
    async def listthemes(self, ctx):
        """List the themes and available features"""
        outs = {i: [] for i in themes.list}
        for x in themes.list:
            for y in self.feature_list:
                if self.feature_list[y] in themes.list[x].__dict__:
                    outs[x].append((y, "\N{WHITE HEAVY CHECK MARK}"))
                else:
                    outs[x].append((y, "❌"))
        final = tabulate(
            [list(chain([i], *[x[1] for x in j])) for i, j in outs.items()],
            headers=["#"] + list(self.feature_list.keys()),
            tablefmt="presto",
            stralign="center",
        )

        await ctx.send(box(final))

    @chelp.command()
    async def reorder(self, ctx, *, categories: Optional[str] = None):
        """This can be used to reorder the categories.

        The categories you type are pushed forward while the rest are pushed back."""
        if categories:
            content = categories
        else:
            await ctx.send(
                "Your next message should be valid category names each in a new line\n"
                "Example:\n"
                "general\n"
                "fun\n"
                "moderation\n"
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
        content = map(str.strip, content.split())
        to_config = []
        failed = []
        for cat_name in content:
            try:
                to_config.append(GLOBAL_CATEGORIES.index(cat_name))
            except ValueError:
                failed.append(cat_name)

        async with self.config.categories() as cat_conf:
            new_order = [cat_conf[cat_index] for cat_index in to_config]

            for ind in range(len(cat_conf)):
                if ind not in to_config:
                    new_order.append(cat_conf[ind])

            cat_conf[:] = new_order

        await self.refresh_cache()
        await ctx.send(
            "Successfully reordered the categories\n"
            + (
                "Invalid categories: (uncategorised is invalid as well)\n" + "\n".join(failed)
                if failed
                else ""
            )
        )

    @commands.command(aliases=["findcat"])
    async def findcategory(self, ctx, *, command):
        """Get the category where the command is present"""
        # TODO check for cog here as well.
        if cmd := self.bot.get_command(command):
            em = discord.Embed(title=f"{command}", color=await ctx.embed_color())
            if cmd.cog:
                cog_name = cmd.cog.__class__.__name__
                for cat in GLOBAL_CATEGORIES:
                    if cog_name in cat.cogs:
                        em.add_field(name="Category:", value=cat.name, inline=False)
                        em.add_field(name="Cog:", value=cog_name, inline=False)
                        await ctx.send(embed=em)
                        break
                else:
                    await ctx.send("Impossible! report this to the cog owner of customhelp pls")
            else:
                em.add_field(name="Category:", value=GLOBAL_CATEGORIES.category.name, inline=False)
                em.add_field(name="Cog:", value="None", inline=False)
                await ctx.send(embed=em)
        else:
            await ctx.send("Command not found")

    def _update_conf(self, var, key, value):
        """Sample:
        var = settings
        key = thumbnail
        value= https://some_url.com"""

        # Only change if it's customhelp formatter
        if isinstance(self.bot._help_formatter, BaguetteHelp):
            getattr(self.bot._help_formatter, var)[key] = value

    async def parse_yaml(self, ctx, content):
        """Parse the yaml with basic structure checks"""
        # TODO make this as an util function?
        try:
            parsed_data = yaml.safe_load(content)
        except (yaml.parser.ParserError, yaml.constructor.ConstructorError):
            await ctx.send("Wrongly formatted")
            return
        except yaml.scanner.ScannerError as e:
            await ctx.send(box(str(e).replace("`", "\N{ZWSP}`")))
            return
        if type(parsed_data) != dict:
            await ctx.send("Invalid Format, Missed a colon probably")
            return

        # TODO pls get a better type checking method
        for i in parsed_data:
            if type(parsed_data[i]) != list:
                await ctx.send("Invalid Format, Likely added unwanted spaces")
                return
        return parsed_data
