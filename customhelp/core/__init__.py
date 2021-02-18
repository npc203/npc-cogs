from .dpy_menus import NoReplyMenus, ReplyMenus
from redbot import __version__

# Keeping all global vars in one place
GLOBAL_CATEGORIES = []
ARROWS = {
    "right": "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}",
    "left": "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
    "cross": "\N{CROSS MARK}",
    "home": "\U0001f3d8\U0000fe0f",
}
# TODO this is lame, get an actual method
BaseMenu = []


def set_menu(reply: bool):
    global BaseMenu
    if reply:
        if __version__ >= "3.4.6":
            BaseMenu[:] = [ReplyMenus]
            return "Sucessfully enabled replies for help menus", 1
        else:
            return "You need to have Red version 3.4.6 or greater to use replies", 0
    else:
        BaseMenu[:] = [NoReplyMenus]
        return "Sucessfully disabled replies for help menus", 1
