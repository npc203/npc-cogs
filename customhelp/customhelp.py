import asyncio
import json
import re
from collections import Counter, defaultdict
from inspect import getfile
from itertools import chain
from os import path
from pathlib import Path
from types import MethodType
from typing import Dict, List, Literal, Union

import discord
import yaml
from discord.ext import commands as dpy_commands
from tabulate import tabulate

from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils import menus, predicates
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.predicates import ReactionPredicate

from . import themes
from .core.base_help import EMPTY_STRING, BaguetteHelp
from .core.category import ARROWS, GLOBAL_CATEGORIES, Category, get_category
from .core.utils import EMOJI_REGEX, LINK_REGEX, emoji_converter

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

_ = Translator("Help", __file__)

# Swtichable alphabetic ordered display
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
            }
     ]
    }
"""


class CustomHelp(commands.Cog):
    """
    A custom customisable help for fun and profit
    """

    __version__ = "0.5.3"

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
            "uncategorised": {
                "name": None,
                "desc": None,
                "long_desc": None,
                "reaction": None,
            },
            "settings": {
                "react": True,
                "set_formatter": False,
                "thumbnail": None,
                "arrows": {
                    "right": "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}",
                    "left": "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
                    "cross": "\N{CROSS MARK}",
                    "home": "\U0001f3d8\U0000fe0f",
                },
            },
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
        arrows = await self.config.settings.arrows()
        for name, emoji in arrows.items():
            if emj := emoji_converter(self.bot, emoji):
                ARROWS[name] = emj
            else:
                # back-up measure if the something went wrong
                ARROWS[name] = self.chelp_global["settings"]["arrows"][name]

    async def refresh_cache(self):
        """Get's the config and re-populates the GLOBAL_CATEGORIES"""
        # Blocking?
        # await self.config.clear_all()
        my_categories = await self.config.categories()
        # GLOBAL_CATEGORIES[:] = [Category(**i) for i in my_categories]
        # Refreshing arrows idk why i made this a task tho
        asyncio.create_task(self.refresh_arrows())
        # Correct the emoji types
        GLOBAL_CATEGORIES[:] = []
        for cat in my_categories:
            cat_obj = Category(**cat)
            cat_obj.reaction = emoji_converter(self.bot, cat_obj.reaction)
            GLOBAL_CATEGORIES.append(cat_obj)

        # make the uncategorised cogs
        all_loaded_cogs = set(self.bot.cogs.keys())
        uncategorised = all_loaded_cogs - set(
            chain(*(category["cogs"] for category in my_categories))
        )

        uncat_config = await self.config.uncategorised()
        GLOBAL_CATEGORIES.append(
            Category(
                name=uncat_config["name"] if uncat_config["name"] else "uncategorised",
                desc=uncat_config["desc"] if uncat_config["desc"] else "No category commands",
                long_desc=uncat_config["long_desc"] if uncat_config["long_desc"] else "",
                reaction=emoji_converter(self.bot, uncat_config["reaction"]),
                cogs=list(uncategorised),
            )
        )

    async def _setup(self):
        """Adds the themes and loads the formatter"""
        # This is needed to be on top so that Cache gets populated no matter what (supplements chelp create)
        await self.refresh_cache()

        # backward compatible removal
        if self.__version__ <= "0.4.0" and "url" in await self.config.settings():
            async with self.config.settings() as conf:
                del conf["url"]

        if not (await self.config.settings.set_formatter()):
            return
        main_theme = BaguetteHelp(self.bot, self.config)
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

    @commands.Cog.listener("on_cog_add")
    async def handle_new_cog_entries(self, cog: commands.Cog):
        cog_name = cog.__class__.__name__
        # More work on this please
        if GLOBAL_CATEGORIES:
            for cat in GLOBAL_CATEGORIES:
                if cog_name in cat.cogs:
                    break
            else:
                GLOBAL_CATEGORIES[-1].cogs.append(cog_name)

    @checks.is_owner()
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

    @chelp.command(aliases=["auto", "autocat"])
    async def autocategorise(self, ctx):
        """Auto categorise cogs based on it's tags"""
        data = {}
        # Thanks trusty pathlib is awesome.
        for k, a in self.bot.cogs.items():
            check = Path(getfile(a.__class__)).parent / "info.json"
            if path.isfile(check):
                with open(check, "r", encoding="utf-8") as f:
                    tmp = json.load(f)
                    if "tags" in tmp:
                        data[k] = [i.lower() for i in tmp["tags"]]
                    else:
                        data[k] = []
            else:
                data[k] = []

        # Ofc grouping was done with the help random ppl helping me in pydis guild+stackoverflow :aha:
        popular = Counter(chain.from_iterable(data.values()))
        groups = defaultdict(set)
        for key, tags in data.items():
            if tags:
                tag = max(tags, key=popular.get)
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
        arrows = await self.config.settings.arrows()
        setting_mapping = {
            "react": "usereactions",
            "set_formatter": "iscustomhelp?",
            "thumbnail": "thumbnail",
        }
        other_settings = []
        # url doesnt exist now, that's why the check. sorry guys.
        for i, j in settings.items():
            if i in setting_mapping:
                other_settings.append(f"`{setting_mapping[i]:<13}`: {j}")
        val = await self.config.theme()
        val = "\n".join([f"`{i:<10}`: " + (j if j else "default") for i, j in val.items()])
        emb = discord.Embed(title="Custom help settings", color=await ctx.embed_color())
        emb.add_field(name="Theme", value=val)
        emb.add_field(
            name="Other Settings",
            value="\n".join(other_settings),
            inline=False,
        )
        emb.add_field(
            name="Arrows",
            value="\n".join(f"`{i:<7}`: {j}" for i, j in arrows.items()),
            inline=False,
        )
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

    @chelp.command(name="set")
    async def set_formatter(self, ctx, setval: bool):
        """Set to toggle custom formatter or the default help formatter\n`[p]chelp set 0` to turn custom off \n`[p]chelp set 1` to turn it on"""
        async with ctx.typing():
            try:
                if setval:
                    # TODO potiential save a config call?
                    await self.config.settings.set_formatter.set(True)
                    await self._setup()
                    await ctx.send("Fomatter set to custom")
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
                "Your next message should be a yaml with the specfied format as in the docs\n"
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
                await ctx.send("Invalid Format!")
                return

        available_categories = [category.name for category in GLOBAL_CATEGORIES]
        # Remove uncategorised
        available_categories.pop(-1)
        # Not using cache (GLOBAL_CATEGORIES[-1].cogs) cause cog unloads aren't tracked
        all_cogs = set(self.bot.cogs.keys())
        uncategorised = all_cogs - set(
            chain(*(category.cogs for category in GLOBAL_CATEGORIES[:-1]))
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

        # {"new": [{cat_conf_structure,...}, {...}] , "existing": { index: [cogs], ..}}
        to_config = {"new": [], "existing": {}}
        for category in parsed_data:
            # check if category exist
            if category in available_categories:
                # update the existing category
                index = available_categories.index(category)
                if index in to_config["existing"]:
                    to_config["existing"][index].extend(parse_to_config(category)["cogs"])
                else:
                    to_config["existing"][index] = parse_to_config(category)["cogs"]
            else:
                to_config["new"].append(parse_to_config(category))

        # Writing to config
        async with self.config.categories() as conf_cat:
            conf_cat.extend(to_config["new"])
            for cat_index in to_config["existing"]:
                conf_cat[cat_index]["cogs"].extend(to_config["existing"][cat_index])

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
    async def edit(self, ctx, *, yaml_txt=None):
        """Add reactions and descriptions to the category"""
        if yaml_txt:
            content = yaml_txt
        else:
            await ctx.send(
                "Your next message should be a yaml with the specfied format as in the docs\n"
                "Example:\n"
                "category1:\n"
                " - name: newname(use this ONLY for renaming)\n - reaction: \U0001f604\n - desc: short description\n - long_desc: long description (Optional,only displayed in dank theme)"
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
                await ctx.send("Invalid Format!")
                return
        # Some more rearrangement parsed_data = {category:[('name', 'notrandom'), ('emoji', 'asds'), ('emoji', '😓'), ('desc', 'this iasdiuasd')]}
        parsed_data = {
            i: [(k, v) for f in my_list for k, v in f.items()]
            for i, my_list in parsed_data.items()
        }
        check = ["name", "desc", "long_desc", "reaction"]
        available_categories = [category.name for category in GLOBAL_CATEGORIES]
        # Remove uncategorised
        available_categories.pop(-1)
        # Not using cache (GLOBAL_CATEGORIES[-1].cogs) cause cog unloads aren't tracked
        all_cogs = set(self.bot.cogs.keys())
        already_present_emojis = list(
            str(i.reaction) for i in GLOBAL_CATEGORIES if i.reaction
        ) + list((await self.config.settings.arrows()).values())
        failed = []  # example: [('desc','categoryname')]

        # special naming for uncategorized stuff
        uncat_name = GLOBAL_CATEGORIES[-1].name

        def validity_checker(category, item):
            if item[0] in check:
                if item[0] == "name":
                    return not (item[1] in available_categories)
                # dupe emoji and valid emoji?
                elif item[0] == "reaction":
                    if item[1] not in already_present_emojis or re.search(EMOJI_REGEX, item[1]):
                        return True
                    else:
                        return False
                else:
                    return True

        # TODO bunch the config calls?
        for category in parsed_data:
            if uncat_name == category:
                async with self.config.uncategorised() as unconf_cat:
                    for item in parsed_data[category]:
                        if validity_checker(category, item):
                            unconf_cat[item[0]] = item[1]
                        else:
                            failed.append((item, category))
                        continue
            elif category in available_categories:
                async with self.config.categories() as conf_cat:
                    cat_index = available_categories.index(category)
                    for item in parsed_data[category]:
                        if validity_checker(category, item):
                            conf_cat[cat_index][item[0]] = item[1]
                        else:
                            failed.append((item, category))
            else:
                # TODO make this a lil neater for Everything failed?
                failed.append((("[Not a valid category name]", "Everything"), category))
        for page in pagify(
            f"Successfully added the edits"
            if not failed
            else "The following things failed:\n"
            + "\n".join(
                [f"{reason[0]}: {reason[1]}  failed in {category}" for reason, category in failed]
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
        available_categories = (category["name"] for category in available_categories_raw)
        all_cogs = set(self.bot.cogs.keys())
        uncategorised = all_cogs - set(
            chain(*(category["cogs"] for category in available_categories_raw))
        )
        joined = (
            _("Set Categories:\n") if len(available_categories_raw) > 1 else _("Set Category:\n")
        )
        for category in available_categories_raw:
            joined += "+ {}:\n".format(category["name"])
            for cog in sorted(category["cogs"]):
                joined += "  - {}\n".format(cog)
        joined += "\n+ {}:\n".format("uncategorised")
        for name in sorted(uncategorised):
            joined += "  - {}\n".format(name)
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

    @chelp.command()
    async def reset(self, ctx):
        """Resets all settings to default **custom** help \n use `[p]chelp set 0` to revert back to the old help"""
        msg = await ctx.send("Are you sure? This will reset everything back to the default theme.")
        menus.start_adding_reactions(msg, predicates.ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = predicates.ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            self.bot.reset_help_formatter()
            self.bot.set_help_formatter(BaguetteHelp(self.bot, self.config))
            await self.config.theme.set(
                {"cog": None, "category": None, "command": None, "main": None}
            )
            await ctx.send("Reset successful")
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
            await self.config.clear_all()
            self.config.register_global(**self.chelp_global)
            await ctx.send("Cleared all categories")
            await self.refresh_cache()
            return
        await ctx.send("Aborted")

    # TODO need to remove multiple categories?
    @remove.command()
    async def category(self, ctx, category: str):
        """Remove a single category"""
        all_cat = await self.config.categories()
        all_cat = [i["name"] for i in all_cat]
        if category in all_cat:
            async with self.config.categories() as conf_cat:
                conf_cat.pop(all_cat.index(category))
            await self.refresh_cache()
            await ctx.send(f"Successfully removed {category}")
        # uncategorised
        elif category == GLOBAL_CATEGORIES[-1].name:
            await ctx.send(
                f"You can't remove {category} cause it is where the uncategorised cogs go into"
            )
        else:
            await ctx.send(f"Invalid category name: {category}")

    # TODO need to remove multiple cogs?
    @remove.command()
    async def cog(self, ctx, cog_name: str):
        """Remove a cog from a category"""
        # valid cog
        if self.bot.get_cog(cog_name):
            for cat in GLOBAL_CATEGORIES:
                if cog_name in cat.cogs:
                    if cat == GLOBAL_CATEGORIES[-1]:
                        await ctx.send("You can't remove cogs from uncategorised category")
                        return
                    async with self.config.categories() as cat_conf:
                        cat_conf[GLOBAL_CATEGORIES.index(cat)]["cogs"].remove(cog_name)
                    await ctx.send(f"Successfully removed {cog_name} from {cat.name}")
                    await self.refresh_cache()
                    return
            else:
                # idk when this might happen, so having it.
                await ctx.send("Something went wrong, report to cog owner")
        else:
            await ctx.send(f"Invaild cog name:`{cog_name}`")

    @chelp.group()
    async def settings(self, ctx):
        """Change various help settings"""

    @settings.command(aliases=["usereaction"])
    async def usereactions(self, ctx, toggle: bool):
        """Toggles adding reaction for navigation."""
        async with self.config.settings() as f:
            f["react"] = toggle
        await ctx.tick()

    @settings.command(aliases=["setthumbnail"])
    async def thumbnail(self, ctx, url: str = None):
        """Set your thumbnail image here.\n use `[p]chelp settings thumbnail` to reset this"""
        if url:
            if re.search(LINK_REGEX, url):
                async with self.config.settings() as f:
                    f["thumbnail"] = url
                await ctx.tick()
            else:
                await ctx.send("Enter a valid url")
        else:
            async with self.config.settings() as f:
                f["thumbnail"] = None
            await ctx.send("Reset thumbnail")

    @settings.command(aliases=["arrow"])
    async def arrows(self, ctx, *, correct_txt=None):
        """Add custom arrows for fun and profit"""
        if correct_txt:
            content = correct_txt
        else:
            await ctx.send(
                "Your next message should be with the specfied format as in the docs\n"
                "Example:\n"
                "left: ↖️\n"
                "right:↗️\n"
                "cross:❎"
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

        already_present_emojis = list(
            str(i.reaction) for i in GLOBAL_CATEGORIES if i.reaction
        ) + list((await self.config.settings.arrows()).values())

        async def emj_parser(data):
            parsed = {}
            checks = ["left", "right", "cross", "home"]
            raw = data.split("\n")
            for emj in raw:
                tmp = emj.split(":", 1)
                tmp = [i.strip() for i in tmp]
                if len(tmp) != 2 or tmp[0] not in checks:
                    await ctx.send("Invalid format")
                    return
                else:
                    if tmp[1] not in already_present_emojis:
                        if emoji_converter(self.bot, tmp[1]):
                            parsed[tmp[0]] = tmp[1]
                        else:
                            await ctx.send(f"Invalid Emoji:{tmp[1]}")
                            return
                    else:
                        await ctx.send(f"Already present Emoji:{tmp[1]}")
                        return
            return parsed

        parsed_data = await emj_parser(content)
        if not parsed_data:
            return
        async with self.config.settings.arrows() as conf:
            for k, v in parsed_data.items():
                conf[k] = v
        await ctx.send(
            "Successfully added the changes:\n"
            + "\n".join(f"`{i} `: {j}" for i, j in parsed_data.items())
        )

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
                        await ctx.send(f"Sucessfully added {category} to nsfw category")
                    else:
                        await ctx.send(f"{category} is already present in nsfw blocklist")
        else:
            await ctx.send("Invalid category name")

    @nsfw.command(name="remove")
    async def remove_nsfw(self, ctx, category: str):
        if cat_obj := get_category(category):
            async with self.config.blacklist.nsfw() as conf:
                if category in conf:
                    conf.remove(category)
                    await ctx.send(f"Sucessfully removed {category} from nsfw category")
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
                        await ctx.send(f"Sucessfully added {category} to dev list")
                    else:
                        await ctx.send(f"{category} is already present in dev list")
        else:
            await ctx.send("Invalid category name")

    @dev.command(name="remove")
    async def remove_dev(self, ctx, category: str):
        if cat_obj := get_category(category):
            async with self.config.blacklist.dev() as conf:
                if category in conf:
                    conf.remove(category)
                    await ctx.send(f"Sucessfully removed {category} from dev category")
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
                    await ctx.send("Impossible! report this to the cog owner pls")
            else:
                em.add_field(name="Category:", value=GLOBAL_CATEGORIES[-1].name, inline=False)
                em.add_field(name="Cog:", value="None", inline=False)
                await ctx.send(embed=em)
        else:
            await ctx.send("Command not found")

    async def parse_yaml(self, ctx, content):
        """Parse the yaml with basic structure checks"""
        # TODO make this as an util function?
        try:
            parsed_data = yaml.safe_load(content)
        except yaml.parser.ParserError:
            await ctx.send("Wrongly formatted")
            return
        except yaml.scanner.ScannerError as e:
            await ctx.send(box(e))
            return
        if type(parsed_data) != dict:
            await ctx.send("Invalid Format")
            return

        # TODO pls get a better type checking method
        for i in parsed_data:
            if type(parsed_data[i]) != list:
                await ctx.send("Invalid Format")
                return
        return parsed_data

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
