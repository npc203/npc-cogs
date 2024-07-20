import re
import textwrap
from collections import namedtuple

import discord
from html2text import html2text as h2t
from redbot.core.utils.chat_formatting import pagify
from redbot.vendored.discord.ext import menus

nsfwcheck = lambda ctx: (not ctx.guild) or ctx.channel.is_nsfw()

s = namedtuple("searchres", "url title desc")


def reply(ctx):
    # Helper reply grabber
    if hasattr(ctx.message, "reference") and ctx.message.reference is not None:
        msg = ctx.message.reference.resolved
        if isinstance(msg, discord.Message):
            return msg


def get_url(msg_obj, check=False):
    # Helper get potential url, if check is True then returns none if nothing is found in embeds
    if msg_obj.embeds:
        emb = msg_obj.embeds[0].to_dict()
        if "image" in emb:
            return emb["image"]["url"]
        elif "thumbnail" in emb:
            return emb["thumbnail"]["url"]
    if msg_obj.attachments:
        return msg_obj.attachments[0].url
    else:
        return None if check else msg_obj.content.lstrip("<").rstrip(">")


def check_url(url: str):
    # Helper function to check if valid url or not
    return url.startswith("http") and " " not in url


def get_query(ctx, url):
    query = None
    if resp := reply(ctx):
        query = get_url(resp)

    # TODO More work on this to shorten code.
    if not query or not check_url(query):
        if query := get_url(ctx.message, check=True):
            pass
        elif url is None:
            return
        else:
            query = url.lstrip("<").rstrip(">")

    # Big brain url parsing
    if not check_url(query):
        return
    if not query or not query.startswith("http") or " " in query:
        return

    return query


def get_card(soup, final, kwargs):
    """Getting cards if present, here started the pain"""
    # common card
    if card := soup.select_one("div.g.mnr-c.g-blk"):
        if desc := card.find("span", class_="hgKElc"):
            final.append(s(None, "Google Info Card:", h2t(str(desc))))
            return
    # another webpull card: what is the language JetBrains made? TODO fix this, depends on too many classes as of now
    if card := soup.select("div.kp-blk.c2xzTb"):
        if head := card.select("div.Z0LcW.XcVN5d.AZCkJd"):
            if desc := card.find("div", class_="iKJnec"):
                final.append(s(None, f"Answer: {head.text}", h2t(str(desc))))
                return

    # calculator card
    if card := soup.find("div", class_="tyYmIf"):
        if question := card.find("span", class_="vUGUtc"):
            if answer := card.find("span", class_="qv3Wpe"):
                tmp = h2t(str(question)).strip("\n")
                final.append(s(None, "Google Calculator:", f"**{tmp}** {h2t(str(answer))}"))
                return

    # sidepage card
    if card := soup.find("div", class_="osrp-blk"):
        if thumbnail := card.find("g-img", attrs={"data-lpage": True}):
            kwargs["thumbnail"] = thumbnail["data-lpage"]
        if title := card.find("div", class_=re.compile("ZxoDOe")):
            if desc := soup.find("div", class_=re.compile("qDOt0b|kno-rdesc")):
                if remove := desc.find(class_=re.compile("Uo8X3b")):
                    remove.decompose()

                desc = textwrap.shorten(h2t(str(desc.span)), 1024, placeholder="...") + "\n"

                if more_info := soup.findAll("div", class_="Z1hOCe"):
                    for thing in more_info:
                        tmp = thing.findAll("span")
                        if len(tmp) >= 2:
                            desc2 = f"\n **{tmp[0].text}**`{tmp[1].text.lstrip(':')}`"
                            # More jack advises :D
                            MAX = 1024
                            MAX_LEN = MAX - len(desc2)
                            if len(desc) > MAX_LEN:
                                desc = (
                                    next(
                                        pagify(
                                            desc,
                                            delims=[" ", "\n"],
                                            page_length=MAX_LEN - 1,
                                            shorten_by=0,
                                        )
                                    )
                                    + "\N{HORIZONTAL ELLIPSIS}"
                                )
                            desc = desc + desc2
                final.append(
                    s(
                        None,
                        "Google Featured Card: "
                        + h2t(str(title)).replace("\n\n", "\n").replace("#", ""),
                        desc,
                    )
                )
            return

    # time cards and unit conversions and moar-_- WORK ON THIS, THIS IS BAD STUFF 100
    if card := soup.find("div", class_="vk_c"):
        if conversion := card.findAll("div", class_="rpnBye"):
            if len(conversion) != 2:
                return
            tmp = tuple(
                map(
                    lambda thing: (
                        thing.input["value"],
                        thing.findAll("option", selected=True)[0].text,
                    ),
                    conversion,
                )
            )
            final.append(
                s(
                    None,
                    "Unit Conversion v1:",
                    "`" + " ".join(tmp[0]) + " is equal to " + " ".join(tmp[1]) + "`",
                )
            )
            return
        elif card.find("div", "lu_map_section"):
            if img := re.search(r"\((.*)\)", h2t(str(card)).replace("\n", "")):
                kwargs["image"] = "https://www.google.com" + img[1]
                return
        else:
            # time card
            if tail := card.find("table", class_="d8WIHd"):
                tail.decompose()
            tmp = h2t(str(card)).replace("\n\n", "\n").split("\n")
            final.append(s(None, tmp[0], "\n".join(tmp[1:])))
            return

    # translator cards
    if card := soup.find("div", class_="tw-src-ltr"):
        langs = soup.find("div", class_="pcCUmf")
        src_lang = "**" + langs.find("span", class_="source-language").text + "**"
        dest_lang = "**" + langs.find("span", class_="target-language").text + "**"
        final_text = ""
        if source := card.find("div", id="KnM9nf"):
            final_text += (src_lang + "\n`" + source.find("pre").text) + "`\n"
        if dest := card.find("div", id="kAz1tf"):
            final_text += dest_lang + "\n`" + dest.find("pre").text.strip("\n") + "`"
        final.append(s(None, "Google Translator", final_text))
        return

    # Unit conversions
    if card := soup.find("div", class_="nRbRnb"):
        final_text = "\N{ZWSP}\n**"
        if source := card.find("div", class_="vk_sh c8Zgcf"):
            final_text += "`" + h2t(str(source)).strip("\n")
        if dest := card.find("div", class_="dDoNo ikb4Bb gsrt gzfeS"):
            final_text += " " + h2t(str(dest)).strip("\n") + "`**"
        if time := card.find("div", class_="hqAUc"):
            if remove := time.find("select"):
                remove.decompose()
            tmp = h2t(str(time)).replace("\n", " ").split("·")
            final_text += (
                "\n"
                + (f"`{tmp[0].strip()}` ·{tmp[1]}" if len(tmp) == 2 else "·".join(tmp))
                + "\n\N{ZWSP}"
            )
        final.append(s(None, "Unit Conversion", final_text))
        return

    # Definition cards -
    if card := soup.find("div", class_="KIy09e"):
        final_text = ""
        if word := card.find("div", class_="ya2TWb"):
            if sup := word.find("sup"):
                sup.decompose()
            final_text += "`" + word.text + "`"

        if pronounciate := card.find("div", class_="S23sjd"):
            final_text += "   |   " + pronounciate.text

        if type_ := card.find("span", class_="YrbPuc"):
            final_text += "   |   " + type_.text + "\n\n"

        if definition := card.find("div", class_="LTKOO sY7ric"):
            if remove_flex_row := definition.find(class_="bqVbBf jfFgAc CqMNyc"):
                remove_flex_row.decompose()

            for text in definition.findAll("span"):
                tmp = h2t(str(text))
                if tmp.count("\n") < 5:
                    final_text += "`" + tmp.strip("\n").replace("\n", " ") + "`" + "\n"

        final.append(s(None, "Definition", final_text))
        return

    # single answer card
    if card := soup.find("div", class_="ayRjaf"):
        final.append(
            s(
                None,
                h2t(str(card.find("div", class_="zCubwf"))).replace("\n", ""),
                h2t(str(card.find("span").find("span"))).strip("\n") + "\n\N{ZWSP}",
            )
        )
        return
    # another single card?
    if card := soup.find("div", class_="sXLaOe"):
        final.append(s(None, "Single Answer Card:", card.text))
        return


# Dpy menus
class Source(menus.ListPageSource):
    async def format_page(self, menu, embeds):
        return embeds


# Thanks fixator https://github.com/fixator10/Fixator10-Cogs/blob/V3.leveler_abc/leveler/menus/top.py
class ResultMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            timeout=60,
            clear_reactions_after=True,
            delete_message_after=True,
        )

    def _skip_double_triangle_buttons(self):
        return super()._skip_double_triangle_buttons()

    async def finalize(self, timed_out):
        if timed_out and self.delete_message_after:
            self.delete_message_after = False

    @menus.button(
        "\u23ee\ufe0f",
        position=menus.First(0),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_first_page(self, payload):
        """go to the first page"""
        await self.show_page(0)

    @menus.button("\u2b05\ufe0f", position=menus.First(1))
    async def go_to_previous_page(self, payload):
        """go to the previous page"""
        if self.current_page == 0:
            await self.show_page(self._source.get_max_pages() - 1)
        else:
            await self.show_checked_page(self.current_page - 1)

    @menus.button("\u27a1\ufe0f", position=menus.Last(0))
    async def go_to_next_page(self, payload):
        """go to the next page"""
        if self.current_page == self._source.get_max_pages() - 1:
            await self.show_page(0)
        else:
            await self.show_checked_page(self.current_page + 1)

    @menus.button(
        "\u23ed\ufe0f",
        position=menus.Last(1),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_last_page(self, payload):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(self._source.get_max_pages() - 1)

    @menus.button("\N{CROSS MARK}", position=menus.First(2))
    async def stop_pages(self, payload) -> None:
        self.stop()
