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

    @checks.bot_has_permissions(manage_webhooks=True, manage_messages=True)
    @commands.command()
    async def tell(self, ctx, *, sentence: str):
        """Tells the given text as the yourself but with a bot tag"""
        hook = await self.get_hook(ctx)
        await ctx.message.delete()
        await hook.send(
            username=ctx.author.display_name,
            avatar_url=ctx.author.avatar_url,
            content=sentence,
        )

    @checks.bot_has_permissions(manage_webhooks=True, manage_messages=True)
    @commands.command()
    async def tellas(self, ctx, mention: discord.Member, *, sentence: str):
        """Tells the given text as the mentioned users"""
        hook = await self.get_hook(ctx)
        await ctx.message.delete()
        await hook.send(
            username=mention.display_name,
            avatar_url=mention.avatar_url,
            content=sentence,
        )

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

    async def print_it(self, ctx, stuff: str):
        hook = await self.get_hook(ctx)
        await hook.send(
            username=ctx.message.author.display_name,
            avatar_url=ctx.message.author.avatar_url,
            content=stuff,
        )

    async def get_hook(self, ctx):
        try:
            if ctx.channel.id not in self.cache:
                for i in await ctx.channel.webhooks():
                    if i.user.id == self.bot.user.id:
                        hook = i
                        self.cache[ctx.channel.id] = hook
                        break
                else:
                    hook = await ctx.channel.create_webhook(
                        name="red_bot_hook_" + str(ctx.channel.id)
                    )
            else:
                hook = self.cache[ctx.channel.id]
        except discord.errors.NotFound:  # Probably user deleted the hook
            hook = await ctx.channel.create_webhook(name="red_bot_hook_" + str(ctx.channel.id))

        return hook

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
