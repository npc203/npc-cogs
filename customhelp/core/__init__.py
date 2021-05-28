from discord import __version__ as dpy_version

from .dpy_menus import NoReplyMenus, ReplyMenus, get_button_menu

# Keeping all global vars in one place
GLOBAL_CATEGORIES = []
ARROWS = {}

__BaseMenu = None


def set_menu(*, replies: bool, buttons: bool):
    global __BaseMenu
    if replies:
        if dpy_version <= "1.5.0":
            return "You need to have discord.py version 1.6.0 or greater to use replies.", False
        __BaseMenu = ReplyMenus
        return "Enabled replies for help menus.", True
    elif buttons:
        try:
            __BaseMenu = get_button_menu()
        except RuntimeError as error:
            return str(error), 0
        return "Enabled buttons for help menus.", True
    else:
        __BaseMenu = NoReplyMenus
        return "Reset the help menu to vanilla.", True


# wew thanks jack
def get_menu():
    return __BaseMenu
