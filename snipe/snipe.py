import calendar
import time
from collections import defaultdict, deque
from sys import getsizeof
from typing import List, Mapping, Optional

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils import chat_formatting as cf
from redbot.vendored.discord.ext import menus
from redbot_ext_menus import ViewMenu, ViewMenuPages


# https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


# Thanks phen
def recursive_getsizeof(obj: object) -> int:
    total = 0
    if isinstance(obj, Mapping):
        for v in obj.values():
            total += recursive_getsizeof(v)
    else:
        total += getsizeof(obj)
    return total


class MiniMsg:
    __slots__ = ("channel", "author", "content", "embed", "created_at", "deleted_at")

    def __init__(self, msg: discord.Message):
        self.channel = msg.channel
        self.author = msg.author
        self.content = msg.content
        self.embed = msg.embeds[0] if msg.embeds else None
        self.deleted_at = int(time.time())
        self.created_at = int(calendar.timegm(msg.created_at.utctimetuple()))
        # self.attachment = msg.attachments[0] if msg.attachments else None


class EditMsg:
    __slots__ = ("channel", "author", "content")

    def __init__(self, old_msg: discord.Message, new_msg: discord.Message):
        self.channel = old_msg.channel
        self.author = old_msg.author
        self.content = list(
            cf.pagify(
                f"**from:**\n{old_msg.content}\n\n**to:**\n{new_msg.content}", page_length=4000
            )
        )
        # TODO embeds


class Snipe(commands.Cog):
    """
    Multi Snipe for fun and non-profit
    """

    __author__ = "npc203 (epic guy#0715)"
    __version__ = "0.6.9"

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nAuthor: {self.__author__}\nCog version: {self.__version__}"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.notrack = set()
        self.deletecache = defaultdict(lambda: deque(maxlen=100))
        self.editcache = defaultdict(lambda: deque(maxlen=100))
        self.config = Config.get_conf(
            self,
            identifier=231923422,
            force_registration=True,
        )
        self.config.register_guild(ignored_channels=[], ignore_guild=False)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild is not None and message.id not in self.notrack:
            conf_data = await self.config.guild(message.guild).all()
            if (
                not conf_data["ignore_guild"]
                and message.channel.id not in conf_data["ignored_channels"]
            ):
                self.deletecache[message.channel.id].append(MiniMsg(message))
        else:
            self.notrack.remove(message.id)

    @commands.Cog.listener()
    async def on_message_edit(self, old_msg, new_msg):
        if (
            old_msg.guild is not None
            and old_msg.content != new_msg.content
            and old_msg.id not in self.notrack
        ):
            conf_data = await self.config.guild(old_msg.guild).all()
            if (
                not conf_data["ignore_guild"]
                and old_msg.channel.id not in conf_data["ignored_channels"]
            ):
                self.editcache[new_msg.channel.id].append(EditMsg(old_msg, new_msg))

    @staticmethod
    async def pre_check_perms(ctx: commands.Context, channel: discord.TextChannel):
        user_perms = channel.permissions_for(ctx.author)
        if user_perms.read_messages and user_perms.read_message_history:
            return True
        else:
            await ctx.reply(
                f"{ctx.author.name}, you don't have read access to {channel.mention}",
                mention_author=False,
            )
            return False

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def snipe(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
        index: int = None,
    ):
        """
        Snipe a channel's last deleted message for fun and profit.
        you can ignore a channel/server using [p]snipeset ignore
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        msg: Optional[MiniMsg] = None

        if index is None:
            # Getting last message
            for msg_obj in reversed(self.deletecache[channel.id]):
                if msg_obj.content:
                    msg = msg_obj
                    break
        else:
            try:
                msg = self.deletecache[channel.id][-index]
            except IndexError:
                return await ctx.send("Out of range")
        if msg:
            menu = ViewMenuPages(
                source=MsgSource(
                    template_emb=discord.Embed(color=await ctx.embed_color()),
                    entries=[msg],
                    per_page=1,
                ),
                delete_message_after=True,
            )
            await menu.start(ctx)
        else:
            return await ctx.send("Nothing to snipe")

    @snipe.command(name="search")
    async def snipe_search(self, ctx, *, text):
        """search through the history of deleted/edited messages"""
        # TODO remove redundant code
        if self.deletecache[ctx.channel.id]:
            lower_text = text.lower()
            user_msgs = [
                msg
                for msg in reversed(self.deletecache[ctx.channel.id])
                if (msg.content and lower_text in msg.content.lower())
                or (msg.embed and lower_text in str(msg.embed.to_dict()).lower())
            ]
            if user_msgs:
                menu = ViewMenuPages(
                    source=MsgSource(
                        template_emb=discord.Embed(color=await ctx.embed_color()),
                        entries=user_msgs,
                        per_page=1,
                    ),
                    delete_message_after=True,
                )
                await menu.start(ctx)
                if len(user_msgs) > 1:
                    self.notrack.add(menu.message.id)
            else:
                await ctx.send("No snipe'd messages found for the given search text")
        else:
            await ctx.send("Nothing to snipe")

    @snipe.command(name="user")
    async def snipe_user(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: discord.TextChannel = None,
    ):
        """
        Snipe a user's past deleted messages from a text channel.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.deletecache[channel.id]:
            user_msgs = [
                msg
                for msg in reversed(self.deletecache[channel.id])
                if msg.content and msg.author.id == user.id
            ]
            if user_msgs:
                menu = ViewMenuPages(
                    source=MsgSource(
                        template_emb=discord.Embed(color=await ctx.embed_color()),
                        entries=user_msgs,
                        per_page=1,
                    ),
                    delete_message_after=True,
                )
                await menu.start(ctx)
                if len(user_msgs) > 1:
                    self.notrack.add(menu.message.id)
            else:
                await ctx.send("No snipe'd messages found for the user " + str(user))
        else:
            await ctx.send("Nothing to snipe")

    @snipe.command(name="embed")
    async def snipe_embed(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Snipe past embeds in the channel.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if embs_obj := [
            (msg.author, msg.embed) for msg in reversed(self.deletecache[channel.id]) if msg.embed
        ]:
            menu = ViewMenuPages(
                source=EmbSource(embs_obj, per_page=1),
                delete_message_after=True,
            )
            await menu.start(ctx)
            if len(embs_obj) > 1:
                self.notrack.add(menu.message.id)
        else:
            await ctx.send("No embeds to snipe")

    @snipe.command(name="bulk")
    async def snipe_bulk(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        List all recorded snipes in the past for said text channel.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        entries = [msg for msg in reversed(self.deletecache[channel.id]) if msg.content]
        if entries:
            menu = ViewMenuPages(
                source=MsgSource(
                    template_emb=discord.Embed(color=await ctx.embed_color()),
                    entries=entries,
                    per_page=1,
                ),
                delete_message_after=True,
            )
            await menu.start(ctx)
            self.notrack.add(menu.message.id)
        else:
            await ctx.send("Nothing to snipe")

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def esnipe(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
        index: int = None,
    ):
        """
        EditSnipe a channel's last edited message for fun and profit.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.editcache[channel.id]:
            if index is None:
                index = 1
            try:
                msg = self.editcache[channel.id][-index]
                tmplate_emb = discord.Embed(color=await ctx.embed_color())
                tmplate_emb.set_author(name=msg.author, icon_url=msg.author.display_avatar.url)
                menu = VertNavEmbMenus(VerticalNavSource(tmplate_emb, msg))

                async def stop_pages(self, payload) -> None:
                    self.stop()

                menu.add_button(menus.Button("\N{CROSS MARK}", stop_pages, position=menus.First()))
                await menu.start(ctx)
                self.notrack.add(menu.message.id)
            except IndexError:
                await ctx.send("Out of range")
        else:
            return await ctx.send("Nothing to snipe")

    @esnipe.command(name="user")
    async def esnipe_user(
        self,
        ctx: commands.Context,
        user: discord.Member,
        channel: discord.TextChannel = None,
    ):
        """
        Edit Snipe a user's edited messages from the said channel.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        if self.editcache[channel.id]:
            user_msgs = [
                msg
                for msg in reversed(self.editcache[channel.id])
                if msg.content and msg.author.id == user.id
            ]
            if user_msgs:
                menu = HorizontalEditMenus(source=user_msgs, delete_message_after=True)
                await menu.start(ctx)
                self.notrack.add(menu.message.id)
            else:
                await ctx.send("No edit-sniped messages found for the user " + str(user))
        else:
            await ctx.send("Nothing to snipe")

    @esnipe.command(name="bulk")
    async def esnipe_bulk(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        List all recorded edit snipes in the past for said text channel.
        """
        channel = channel or ctx.channel
        pre_check = await self.pre_check_perms(ctx, channel)
        if not pre_check:
            return
        entries = [msg for msg in reversed(self.editcache[channel.id]) if msg.content]
        if entries:
            menu = HorizontalEditMenus(
                source=entries,
                delete_message_after=True,
            )
            await menu.start(ctx)
            self.notrack.add(menu.message.id)
        else:
            await ctx.send("Nothing to snipe")

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def snipeset(self, ctx):
        """Configuration settings for snipe"""

    @snipeset.group(name="ignore")
    async def snipeset_ignore(self, ctx):
        """Ignore channel or server from sniping"""

    @snipeset_ignore.command(name="channel")
    async def snipeset_ignore_channel(
        self, ctx: commands.Context, channel: discord.TextChannel, toggle: bool
    ):
        """Ignore/Unignore a channel for sniping"""
        async with self.config.guild_from_id(ctx.guild.id).ignored_channels() as ignored_channels:
            if toggle:
                if channel.id not in ignored_channels:
                    ignored_channels.append(channel.id)
                else:
                    return await ctx.send("Channel already ignored")
            else:
                if channel.id in ignored_channels:
                    ignored_channels.remove(channel.id)
                else:
                    return await ctx.send("Channel already unignored")
        await ctx.send("Channel " + ("added to" if toggle else "removed from") + " ignore list")

    @snipeset_ignore.command(name="server")
    async def snipeset_ignore_server(self, ctx: commands.Context, toggle: bool):
        """Ignore/Unignore this server for sniping"""
        await self.config.guild_from_id(ctx.guild.id).ignore_guild.set(toggle)
        await ctx.send("Server " + ("added to" if toggle else "removed from") + " ignore list")

    @snipeset.command()
    async def show(self, ctx: commands.Context):
        """Show ignoring channels for the server"""
        data = await self.config.guild_from_id(ctx.guild.id).all()
        emb = discord.Embed(title="Snipe Settings", color=await ctx.embed_color())
        emb.add_field(
            name="Ignoring server:", value="YNeos"[not data["ignore_guild"] :: 2], inline=False
        )
        if not data["ignore_guild"] and data["ignored_channels"]:
            emb.add_field(
                name="Ignored Channels:",
                value="\n".join(str(ctx.guild.get_channel(c)) for c in data["ignored_channels"]),
                inline=False,
            )
        await ctx.send(embed=emb)

    @commands.is_owner()
    @snipeset.command()
    async def stats(self, ctx: commands.Context):
        """Show stats about snipe usage"""
        del_size = recursive_getsizeof(self.deletecache)
        edit_size = recursive_getsizeof(self.editcache)
        emb = discord.Embed(title="Snipe Stats", color=await ctx.embed_color())
        emb.add_field(name="Delete Cache Size", value=sizeof_fmt(del_size))
        emb.add_field(name="Edit Cache Size", value=sizeof_fmt(edit_size))
        emb.add_field(name="Total Cache Size", value=sizeof_fmt(del_size + edit_size))
        emb.add_field(
            name="Cache Entries",
            value="Snipes: {}\nEdits: {}".format(
                sum(len(i) for i in self.deletecache.values()),
                sum(len(i) for i in self.editcache.values()),
            ),
        )
        emb.add_field(
            name="No track msgs (Dev stuff don't mind)",
            value=f"IDs: {len(self.notrack)}\nSize: {sizeof_fmt(getsizeof(self.notrack))}",
            inline=False,
        )
        await ctx.send(embed=emb)

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        return


class MsgSource(menus.ListPageSource):
    def __init__(self, template_emb, **kwargs):
        self.template_emb: discord.Embed = template_emb
        super().__init__(**kwargs)

    async def format_page(self, menu, msg):
        emb = self.template_emb.copy()
        emb.title = f"Message Contents (Sent <t:{msg.created_at}:R>)"
        emb.description = msg.content
        emb.set_author(
            name=f"{msg.author} ({msg.author.id})", icon_url=msg.author.display_avatar.url
        )
        emb.add_field(name="Channel", value=f"<#{msg.channel.id}>")
        emb.add_field(name="Deleted At", value=f"<t:{msg.deleted_at}:R>")
        emb.set_footer(
            text=f"Sniped at {menu.ctx.guild} | Page {menu.current_page+1}/{self._max_pages}",
            icon_url=getattr(menu.ctx.guild.icon, "url", None),
        )

        return emb


class EmbSource(menus.ListPageSource):
    async def format_page(self, menu, entry):
        return {
            "embed": entry[1],
            "content": f"Page {menu.current_page+1}/{self._max_pages}\n{entry[0]}",
        }


class VerticalNavSource(menus.ListPageSource):
    def __init__(self, template_emb, msg: EditMsg):
        self.template_emb = template_emb
        super().__init__(msg.content, per_page=1)

    async def format_page(self, menu, entry):
        emb = self.template_emb.copy()
        emb.description = entry
        return emb


class VertNavEmbMenus(ViewMenuPages, inherit_buttons=False):
    def _skip_single(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages == 1

    @menus.button("\N{UPWARDS BLACK ARROW}", skip_if=_skip_single)
    async def move_up(self, payload):
        await self.show_checked_page(self.current_page - 1)

    @menus.button("\N{DOWNWARDS BLACK ARROW}", skip_if=_skip_single)
    async def move_down(self, payload):
        await self.show_checked_page(self.current_page + 1)


class HorizontalEditMenus(ViewMenu):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs, timeout=60)
        self.message: discord.Message
        self.bot: Red
        self.source: List[EditMsg] = source
        self.max_pages = len(source)
        self.curr_page = 0
        self.vert_page = 0

    async def send_initial_message(self, ctx, channel):
        self.template_embed = discord.Embed(color=await ctx.embed_color())
        emb = self.get_page(0)
        return await self.send_with_view(channel, embed=emb)

    def get_page(self, page_number):
        emb = self.template_embed.copy()
        emb.description = self.source[page_number].content[self.vert_page]
        max_pages_vertical = len(self.source[self.curr_page].content)
        emb.set_footer(
            text=f"Page {page_number+1}/{self.max_pages} | Vertical Page {self.vert_page+1}/{max_pages_vertical}"
        )
        return emb

    async def show_page(self, page_number):
        # Wrap around
        if page_number < 0:
            page_number = self.max_pages - 1
        elif page_number >= self.max_pages:
            page_number = 0
        self.curr_page = page_number
        emb = self.get_page(page_number)
        return await self.message.edit(embed=emb)

    def reaction_check(self, payload):
        """Just extends the default reaction_check to use owner_ids"""
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in (*self.bot.owner_ids, self._author_id):
            return False
        return payload.emoji in self.buttons

    def _skip_double_triangle_buttons(self):
        return self.max_pages <= 3

    async def finalize(self, timed_out):
        if timed_out and self.delete_message_after:
            self.delete_message_after = False

    # Vertical navigation
    @menus.button("\N{UPWARDS BLACK ARROW}", position=menus.Last(0))
    async def move_up(self, payload):
        max_pages_vertical = len(self.source[self.curr_page].content)
        if max_pages_vertical > 1:
            self.vert_page = self.vert_page - 1 if self.vert_page > 0 else max_pages_vertical - 1
            emb = self.get_page(self.curr_page)
            return await self.message.edit(embed=emb)

    @menus.button("\N{DOWNWARDS BLACK ARROW}", position=menus.Last(1))
    async def move_down(self, payload):
        max_pages_vertical = len(self.source[self.curr_page].content)
        if max_pages_vertical > 1:
            self.vert_page = self.vert_page + 1 if self.vert_page < max_pages_vertical - 1 else 0
            emb = self.get_page(self.curr_page)
            return await self.message.edit(embed=emb)

    # Horizontal navigation
    @menus.button(
        "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.First(0),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_first_page(self, payload):
        """go to the first page"""
        self.vert_page = 0
        await self.show_page(0)

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f", position=menus.First(1))
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        self.vert_page = 0
        await self.show_page(self.curr_page - 1)

    @menus.button("\N{CROSS MARK}", position=menus.First(2))
    async def stop_pages(self, payload) -> None:
        self.stop()

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f", position=menus.First(3))
    async def go_to_next_page(self, payload):
        """go to the next page"""
        self.vert_page = 0
        await self.show_page(self.curr_page + 1)

    @menus.button(
        "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.First(4),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_last_page(self, payload):
        """go to the last page"""
        self.vert_page = 0
        await self.show_page(self.max_pages - 1)
