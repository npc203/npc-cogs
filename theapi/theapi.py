from redbot.core import commands, data_manager,checks
import discord
from tabulate import tabulate
from urllib.parse import urlparse
from random import choice
import re,json,aiohttp,os

class API(commands.Cog):
    """Set your own REST api for fun and profit!"""
    def __init__(self, bot):
        self.bot = bot
        self.path = data_manager.cog_data_path(cog_instance="API")
        self._session = aiohttp.ClientSession()
        if os.path.exists(self.path/'cmds.json'):
            with open(self.path/'cmds.json','r') as fp:
                self._cmds = json.load(fp)
        else:
            self._cmds = {}
            with open(self.path/'cmds.json','w') as fp:
                self._cmds = json.dump(self.cmds,fp)
        print(self._cmds)
    
    @checks.is_owner()
    @commands.group()
    async def apiset(self,ctx):
        pass

    @apiset.command()
    async def add(self, ctx,name:str,endpoint:str, returntype:str="image" or "text"):
        existing_command = self._cmds.get(name)
        #The command with built-in name already exists
        if existing_command is None and ctx.bot.get_command(name):
            return await ctx.send(f"A built in command with the name {name} is already registered")
        
        #The api command already exists
        if existing_command:
            return await ctx.send(f"This api command already exists!, use the apiset command instead")
        else:
            #TODO
            help_txt = "No help Section given"
            parsed = urlparse(endpoint)
            @commands.command(name=name, help=help_txt,usage="[]")
            async def cmd(self, ctx):
                async with self._session.get(endpoint) as response:
                    if response.status == 200:
                        await ctx.send(response.content)
                    else:
                        await ctx.send(f"Something went wrong,code:{response.status}")
            cmd.format_help_for_context = lambda ctx : "mycustomstuff"
            cmd.cog = self
            # And add it to the cog and the bot
            #self.__cog_commands__ = self.__cog_commands__ + (cmd,)
            ctx.bot.add_command(cmd)
            # Now add it to our list of custom commands
            self._cmds[name] = {"endpoint":endpoint,"params":{},"help":help_txt}
            await ctx.send(f"Added a command called {name}")




    @commands.command()
    @checks.is_owner()
    async def apilist(self,ctx):
        await ctx.send('```\n'+tabulate([(i,"loaded",self._cmds[i]["help"]) for i in self._cmds],headers=["Commands","Status","Help"])+'```')
            

    @commands.command()
    @checks.is_owner()
    async def apiload(self,ctx,*,endpoints):
        pass

    @commands.command()
    @checks.is_owner()
    async def apiedit(self,ctx,*,cmd:str):
        pass

    @commands.command()
    @checks.is_owner()
    async def apiunload(self,ctx,*,cmd:str):
        pass

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass
    async def cog_unload(self):
        await self._session.close()