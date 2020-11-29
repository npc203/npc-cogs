from io import BytesIO
import discord
import matplotlib.pyplot as plt
from redbot.core.utils import chat_formatting as chat
from redbot.vendored.discord.ext import menus


class WSStatsMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(
        self, source: menus.PageSource, header: str, timeout: int = 30, image: BytesIO = None
    ):
        super().__init__(
            source,
            timeout=timeout,
            clear_reactions_after=True,
            delete_message_after=True,
        )
        self.header = header
        self.image = image

    def should_add_reactions(self):
        return True

    def not_paginating(self):
        return not self._source.is_paginating()

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        msg = await channel.send(
            **kwargs, file=discord.File(self.image, filename="chart.png") if self.image else None
        )
        if self.image:
            self.image.close()
        return msg

    async def finalize(self, timed_out):
        """|coro|
        A coroutine that is called when the menu loop has completed
        its run. This is useful if some asynchronous clean-up is
        required after the fact.
        Parameters
        --------------
        timed_out: :class:`bool`
            Whether the menu completed due to timing out.
        """
        if timed_out and self.delete_message_after:
            self.delete_message_after = False

    async def go_to_first_page(self, payload):
        """go to the first page"""
        await self.show_page(0)

    @menus.button(
        "\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f", position=menus.First(1), skip_if=not_paginating
    )
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        await self.show_checked_page(self.current_page - 1)

    @menus.button(
        "\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f", position=menus.Last(0), skip_if=not_paginating
    )
    async def go_to_next_page(self, payload):
        """go to the next page"""
        await self.show_checked_page(self.current_page + 1)

    @menus.button("\N{CROSS MARK}", position=menus.First(2))
    async def stop_pages(self, payload: discord.RawReactionActionEvent) -> None:
        self.stop()


class WSStatsPager(menus.AsyncIteratorPageSource):
    def __init__(self, entries, add_image: bool = False):
        self.add_image = add_image
        super().__init__(entries, per_page=1)

    async def format_page(self, wsmenu: WSStatsMenu, page):
        e = discord.Embed(
            title=wsmenu.header,
            description=chat.box(page, "ml"),
            color=await wsmenu.ctx.embed_color(),
            timestamp=wsmenu.ctx.bot.uptime,
        )
        if self.add_image:
            e.set_image(url="attachment://chart.png")
        e.set_footer(text=f"Page {wsmenu.current_page + 1}")
        return e


def create_counter_chart(data, title: str):
    plt.clf()
    most_common = data.most_common()
    total = sum(data.values())
    sizes = [(x[1] / total) * 100 for x in most_common][:20]
    labels = [f"{round(sizes[index], 1):.2f}% {x[0]}" for index, x in enumerate(most_common[:20])]
    if len(most_common) > 20:
        others = sum([x[1] / total for x in most_common[20:]])
        sizes.append(others)
        labels.append("{:.2f}% Others".format(others))
    title = plt.title(title, color="white")
    title.set_va("top")
    title.set_ha("center")
    plt.gca().axis("equal")
    colors = [
        "r",
        "darkorange",
        "gold",
        "y",
        "olivedrab",
        "green",
        "darkcyan",
        "mediumblue",
        "darkblue",
        "blueviolet",
        "indigo",
        "orchid",
        "mediumvioletred",
        "crimson",
        "chocolate",
        "yellow",
        "limegreen",
        "forestgreen",
        "dodgerblue",
        "slateblue",
        "gray",
    ]
    pie = plt.pie(sizes, colors=colors, startangle=0)
    plt.legend(
        pie[0],
        labels,
        bbox_to_anchor=(0.7, 0.5),
        loc="center",
        fontsize=10,
        bbox_transform=plt.gcf().transFigure,
        facecolor="#ffffff",
    )
    plt.subplots_adjust(left=0.0, bottom=0.1, right=0.45)
    image_object = BytesIO()
    plt.savefig(image_object, format="PNG", facecolor="#36393E")
    image_object.seek(0)
    return image_object
