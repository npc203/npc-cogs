from redbot.core import commands
import discord

class Speak(commands.Cog):
    """Set of commands to talk as others"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def tell(self,ctx,*,sentence):
        """Tells the given text as the yourself but with a bot tag"""
        hook = await self.get_hook(ctx)
        await ctx.message.delete()
        await hook.send(username=ctx.author.display_name,avatar_url=ctx.author.avatar_url,content=sentence)
    
    @commands.command()
    async def tellas(self, ctx,mention:discord.Member,*,sentence):
        """Tells the given text as the mentioned users"""
        hook = await self.get_hook(ctx)
        await ctx.message.delete()
        await hook.send(username=mention.display_name,avatar_url=mention.avatar_url,content=sentence)
    
    async def get_hook(self,ctx):
        for i in await ctx.channel.webhooks(): #Needs optimisation? cause iterating thro all the webhooks, everytime
            if i.user.id == self.bot.user.id:
                hook = i
                break
        else:
            hook = await ctx.channel.create_webhook(name='bot_hook_'+str(ctx.channel)) 
        
        return hook

    