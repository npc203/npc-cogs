import typing
from random import choice

import discord
from redbot.core import checks, commands, data_manager


class Speak(commands.Cog):
    """Set of commands to talk as others or
    Say stuff for you when you don't have the right words!"""

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        with open(data_manager.bundled_data_path(self) / "insult.txt", encoding="utf8") as fp:
            self.insult_list = fp.read().splitlines()
        with open(data_manager.bundled_data_path(self) / "sadme.txt", encoding="utf8") as fp:
            self.sadme_list = fp.read().splitlines()

    @commands.command()
    async def tell(self, ctx, channel: typing.Optional[discord.TextChannel], *, sentence: str):
        """Tells the given text as the yourself but with a bot tag"""
        if not (channel := await self.invalid_permissions_message(ctx, channel)):
            return

        hook = await self.get_hook(channel)
        if channel == ctx.channel:
            await ctx.message.delete()
        await hook.send(
            username=ctx.author.display_name,
            avatar_url=ctx.author.avatar.url,
            content=sentence,
        )

    @commands.command()
    async def tellas(
        self,
        ctx,
        channel: typing.Optional[discord.TextChannel],
        mention: discord.Member,
        *,
        sentence: str,
    ):
        """Tells the given text as the mentioned users"""
        if not (channel := await self.invalid_permissions_message(ctx, channel)):
            return

        hook = await self.get_hook(channel)
        if channel == ctx.channel:
            await ctx.message.delete()
        await hook.send(
            username=mention.display_name,
            avatar_url=mention.avatar.url,
            content=sentence,
        )

    @checks.bot_has_permissions(manage_webhooks=True, manage_messages=True)
    @commands.command()
    async def telluser(
        self,
        ctx,
        channel: typing.Optional[discord.TextChannel],
        username: str,
        avatar: str,
        *,
        sentence: str,
    ):
        """Says the given text with the specified name and avatar"""
        if not (channel := await self.invalid_permissions_message(ctx, channel)):
            return

        hook = await self.get_hook(channel)
        if channel == ctx.channel:
            await ctx.message.delete()
        if avatar.startswith("http"):
            if 1 < len(username) <= 80:
                await hook.send(
                    username=username,
                    avatar_url=avatar,
                    content=sentence,
                )
            else:
                await ctx.send("You must include a username of less than 80 characters.")
                await ctx.send_help()
        else:
            await ctx.send("You must include a URL to define the webhook avatar.")
            await ctx.send_help()

    @checks.bot_has_permissions(manage_webhooks=True, manage_messages=True)
    @commands.group(invoke_without_command=False)
    async def says(self, ctx):
        """Says Stuff for the user"""
        if ctx.invoked_subcommand is not None:
            await ctx.message.delete()

    @says.command()
    async def insult(self, ctx):
        """says lame insults, use at your own precaution"""
        await self.print_it(ctx, choice(self.insult_list))

    @says.command()
    async def sadme(self, ctx):
        """says depressing stuff about you"""
        await self.print_it(ctx, choice(self.sadme_list))

    async def print_it(self, ctx, stuff: str, retried=False):
        hook = await self.get_hook(ctx.channel)
        try:
            await hook.send(
                username=ctx.message.author.display_name,
                avatar_url=ctx.message.author.avatar.url,
                content=stuff,
            )
        except discord.NotFound:  # Yup user deleted the hook, invalidate cache, retry
            if retried:  # This is an edge case, just a hack to prevent infinite loops
                return await ctx.send("I can't find the webhook, sorry.")
            self.cache.pop(ctx.channel.id)
            await self.print_it(ctx, stuff, True)

    async def get_hook(self, channel: discord.TextChannel):
        try:
            if channel.id not in self.cache:
                for i in await channel.webhooks():
                    if i.user and i.user.id == self.bot.user.id:
                        hook = i
                        self.cache[channel.id] = hook
                        break
                else:
                    hook = await channel.create_webhook(name="red_bot_hook_" + str(channel.id))
            else:
                hook = self.cache[channel.id]
        except discord.NotFound:  # Probably user deleted the hook
            hook = await channel.create_webhook(name="red_bot_hook_" + str(channel.id))
        return hook

    async def invalid_permissions_message(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel]
    ) -> typing.Optional[discord.TextChannel]:
        """Returns target channel if bot and user have valid permissions"""
        if channel is None:
            channel = ctx.channel

        permissions_bot = channel.permissions_for(ctx.guild.me)
        permissions_author = channel.permissions_for(ctx.author)
        if (
            not permissions_bot.manage_webhooks
            or channel == ctx.channel
            and not permissions_bot.manage_messages
        ):
            await ctx.send(
                f"The bot does not have enough permissions to send a webhook in {channel.mention}."
            )
            return
        if (
            not permissions_author.send_messages
            and not permissions_author.read_messages
            and not permissions_author.read_message_history
        ):
            await ctx.send(f"You do not have enough permissions in {channel.mention}.")
            return
        return channel

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
