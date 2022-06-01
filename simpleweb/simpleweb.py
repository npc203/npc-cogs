from typing import Literal
from aiohttp.web_response import json_response
from aiohttp.web_urldispatcher import StaticResource

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from aiohttp import web
import jinja2
import aiohttp_jinja2
import redbot

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


# RPC PORT: 6133 (default)
class SimpleWeb(commands.Cog):
    """
    A simple webpage dashboard
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=3820423,
            force_registration=True,
        )
        self.data_path = redbot.core.data_manager.bundled_data_path(self)
        aiohttp_jinja2.setup(
            bot.rpc.app, loader=jinja2.FileSystemLoader(self.data_path / "templates")
        )
        self.cache = {}

    async def cog_load(self):
        await self.refresh_cache()
        self.routes = {
            "/ping": ("get", self.hello),
            "/": ("get", self.help_commands),
            "/api/cmds": ("get", self.cmd_json),
            "/static": ("static", self.data_path / "static"),
        }

        # Remove older routes
        for path in self.routes:
            for index, resource in enumerate(self.bot.rpc.app.router._resources):
                if isinstance(resource, StaticResource):
                    if resource._prefix == path:
                        self.bot.rpc.app.router._resources.pop(index)
                        break
                elif resource._path == path:
                    self.bot.rpc.app.router._resources.pop(index)
                    break

        self.bot.rpc.app.router._frozen = False
        self.bot.rpc.app.add_routes(
            [getattr(web, obj[0])(k, obj[1]) for k, obj in self.routes.items()]
        )
        self.bot.rpc.app.router._frozen = True

    async def refresh_cache(self):
        self.cache["app_info"] = await self.bot.application_info()
        self.cache["cmds"] = [(c.qualified_name, c.help) for c in self.bot.walk_commands()]

    ### Commands Section ###
    @commands.command("routes")
    async def show_routes(self, ctx):
        await ctx.send(
            embed=discord.Embed(title="Available Routes", description="\n".join(self.routes))
        )

    @commands.command()
    async def refresh_routes(self, ctx):
        await self.refresh_cache()
        await ctx.tick()

    #### ROUTES SECTION ####
    async def help_commands(self, request):
        response = aiohttp_jinja2.render_template("commands.jinja2", request, self.cache)
        return response

    async def hello(self, request) -> web.Response:
        return web.Response(text="Pong! Site working")

    async def cmd_json(self, request):
        return json_response(self.cache["cmds"])

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        return
