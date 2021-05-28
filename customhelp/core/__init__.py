from discord import __version__ as dpy_version

from .dpy_menus import NoReplyMenus, ReplyMenus, get_button_menu

# Keeping all global vars in one place
GLOBAL_CATEGORIES = []
ARROWS = {}

__BaseMenu = ReplyMenus
use_buttons = False


def set_menu(*, replies: bool, buttons: bool, validate_buttons: bool = False):
    global __BaseMenu
    if replies:
        if dpy_version <= "1.5.0":
            return "You need to have discord.py version 1.6.0 or greater to use replies.", False
        __BaseMenu = ReplyMenus
        return "Enabled replies for help menus.", True
    elif buttons:
        if validate_buttons:
            try:
                __BaseMenu = get_button_menu()
            except RuntimeError as error:
                return str(error), 0
        global use_buttons
        use_buttons = True
        return "Enabled buttons for help menus.", True
    else:
        __BaseMenu = NoReplyMenus
        return "Reset the help menu to vanilla.", True


# wew thanks jack
def get_menu():
    global __BaseMenu
    global use_buttons
    if use_buttons:
        try:
            __BaseMenu = get_button_menu()
        except RuntimeError:
            __BaseMenu = ReplyMenus
    return __BaseMenu
