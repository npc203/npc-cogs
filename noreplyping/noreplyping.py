import asyncio
import datetime
from collections import namedtuple

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config


class NoReplyPing(commands.Cog):
    """
    Track the people who reply but turned off their ping
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=3423123,
            force_registration=True,
        )
        self.fake_obj = namedtuple("FakeMessage", "guild")
        self.config.register_member(send_dms=False)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        # Don't bother dms or bots
        if not message.guild or message.author.bot:
            return

        # Phen from AC https://discord.com/channels/133049272517001216/718148684629540905/825041973919744010
        if ref := message.reference:
            ref_message = ref.cached_message or (
                ref.resolved
                if ref.resolved and isinstance(ref.resolved, discord.Message)
                else None
            )
            if not ref_message and ref.message_id:
                ref_chan = message.guild.get_channel(ref.channel_id)
                if isinstance(ref_chan, discord.TextChannel):
                    try:
                        ref_message = await ref_chan.fetch_message(ref.message_id)
                    except (discord.Forbidden, discord.NotFound):
                        pass

            # Valid reply
            if ref_message:
                if any(member.id == ref_message.author.id for member in message.mentions):
                    # User pinged them
                    return
                else:
                    if ref_message.author and ref_message.author.id != message.author.id:
                        if await self.config.member_from_ids(
                            message.guild.id, ref_message.author.id
                        ).send_dms():
                            # wait for 60 seconds before sending dm, so as to not annoy when chatting
                            try:
                                await self.bot.wait_for(
                                    "message",
                                    timeout=60,
                                    check=lambda msg: msg.author.id == ref_message.author.id
                                    and msg.channel.id == message.channel.id,
                                )
                            except asyncio.TimeoutError:
                                emb = discord.Embed(
                                    title=f"Reply from {message.author}",
                                    color=await self.bot.get_embed_color(
                                        self.fake_obj(message.guild)  # type:ignore
                                    ),
                                )
                                emb.description = message.content
                                emb.add_field(
                                    name="Your message",
                                    value=ref_message.content[:1024],
                                    inline=False,
                                )
                                emb.add_field(
                                    name="Reply message Link",
                                    value=f"[Click Here]({message.jump_url})",
                                )
                                emb.timestamp = datetime.datetime.utcnow()
                                await ref_message.author.send(embed=emb)

    @commands.guild_only()  # type:ignore
    @commands.group(invoke_without_command=True, aliases=["nrp"])
    async def noreplyping(self, ctx, toggle: bool):
        """
        Track the people who reply but turned off their ping for this channel.
        bots are ignored by default. It also checks for 15 seconds on inactivity before dm'ing
        """
        await self.config.member_from_ids(ctx.guild.id, ctx.author.id).send_dms.set(toggle)
        await ctx.send(
            f"You will {'now' if toggle else 'NOT'} be dm'ed when someone replies to your message without pinging you, for this guild"
        )

    @commands.is_owner()
    @noreplyping.command(name="stats")
    async def replying_stats(self, ctx):
        """See how many people enabled this command"""
        total = sum(
            sum(1 for i in conf.values() if i["send_dms"])
            for conf in (await self.config.all_members()).values()
        )
        await ctx.send(f"A total of {total:,} member(s) have opted for noreplyping")

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        for g_id, guild in (await self.config.all_members()).items():
            if user_id in guild:
                await self.config.member_from_ids(g_id, user_id).clear()
