from redbot.core import commands
import discord
from random import choice
from pathlib import Path
class Speak(commands.Cog):
    """Set of commands to talk as others"""
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        with open(Path(__file__).parent/"data/insult.pot",encoding="utf8") as fp:
            self.insult = fp.read().splitlines()
        with open(Path(__file__).parent/"data/sadme.pot",encoding="utf8") as fp:
            self.sadme = fp.read().splitlines()
        
    @commands.command()
    async def tell(self,ctx,*,sentence:str):
        """Tells the given text as the yourself but with a bot tag"""
        hook = await self.get_hook(ctx)
        await ctx.message.delete()
        await hook.send(username=ctx.author.display_name,avatar_url=ctx.author.avatar_url,content=sentence)
    
    @commands.command()
    async def tellas(self, ctx,mention:discord.Member,*,sentence:str):
        """Tells the given text as the mentioned users"""
        hook = await self.get_hook(ctx)
        await ctx.message.delete()
        await hook.send(username=mention.display_name,avatar_url=mention.avatar_url,content=sentence)

    @commands.group(invoke_without_command=False)
    async def say(self,ctx):
        """Says Stuff for the user"""
        

    @say.command()
    async def insult(self,ctx):
        """Says lame insults, use at your own precaution"""
        return choice(self.insult)
        
    async def sadme(self,ctx):
        """Says depressing stuff about you"""
        await ctx.invoke(choice(self.sadme))

    async def get_hook(self,ctx):
        try:
            if ctx.channel.id not in self.cache:
                for i in await ctx.channel.webhooks():
                    if i.user.id == self.bot.user.id:
                        hook = i
                        self.cache[ctx.channel.id] = hook
                        break
                else:
                    hook = await ctx.channel.create_webhook(name='red_bot_hook_'+str(ctx.channel.id)) 
            else:
                hook = self.cache[ctx.channel.id]
        except discord.errors.NotFound: #Probably user deleted the hook
            hook = await ctx.channel.create_webhook(name='red_bot_hook_'+str(ctx.channel.id))
            
        return hook


    async def cog_command_error(self,ctx,error):
        if hasattr(error,'original') and isinstance(error.original,discord.errors.Forbidden):
            await ctx.send("Ensure that I have `Manage webhook` and `Manage messages` permissions from the server settings pls.") 
        else: 
            await self.bot.on_command_error(ctx, error, unhandled_by_cog=True)
    
    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
