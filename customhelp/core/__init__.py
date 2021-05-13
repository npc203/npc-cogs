from discord import __version__

from .dpy_menus import NoReplyMenus, ReplyMenus

# Keeping all global vars in one place
GLOBAL_CATEGORIES = []
ARROWS = {}

__BaseMenu = None


def set_menu(reply: bool):
    global __BaseMenu
    if reply:
        if __version__ <= "1.5.0":
            return "You need to have Dpy version 1.6.0 or greater to use replies", 0
        __BaseMenu = ReplyMenus
        return "Sucessfully enabled replies for help menus", 1
    else:
        __BaseMenu = NoReplyMenus
        return "Sucessfully disabled replies for help menus", 1


# wew thanks jack
def get_menu():
    return __BaseMenu
