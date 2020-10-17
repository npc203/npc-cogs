from redbot.core import commands
import discord
from random import choice
from pathlib import Path

class Weeb(commands.Cog):
    """Set of weeby commands to show your otaku-ness
     you can also use 'c' as an additional argument for deleting your message
     Eg:[p]uwu c"""
    def __init__(self, bot):
        self.bot = bot
        with open(Path(__file__).parent/'data/owo.pot','r',encoding="utf8") as f:
            self.owo=f.read().splitlines()
        with open(Path(__file__).parent/'data/uwu.pot','r',encoding="utf8") as f:
            self.uwu=f.read().splitlines()
        with open(Path(__file__).parent/'data/xwx.pot','r',encoding="utf8") as f:
            self.xwx=f.read().splitlines()
        
    @commands.command(aliases=['uWu', 'uwu','UWU'])
    async def UwU(self,ctx,option:str = None):
        """Replies with UwU variant emoticons
        `[p]uwu c` deletes your message"""
        if option == 'c':
            await ctx.message.delete()
        await ctx.send(choice(self.uwu))  

    @commands.command(aliases=['oWo', 'owo','OWO'])
    async def OwO(self,ctx,option:str = None):
        """Replies with OwO variant emoticons
        `[p]owo c` deletes your message"""
        if option == 'c':
            await ctx.message.delete()
        await ctx.send(choice(self.owo))  

    @commands.command()
    async def xwx(self,ctx,option:str = None):
        """Replies with flower girl/yandere girl
        `[p]xwx c` deletes your message"""
        if option == 'c':
            await ctx.message.delete()
        await ctx.send(choice(self.xwx))

    async def cog_command_error(self,ctx,error):
        if hasattr(error,'original') and isinstance(error.original,discord.errors.Forbidden):
            await ctx.send("Ensure that I have `Manage messages` permissions from the server settings pls.") 
        else: 
            await self.bot.on_command_error(ctx, error, unhandled_by_cog=True)

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
