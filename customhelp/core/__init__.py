from discord import __version__ as dpy_version

from .dpy_menus import NoReplyMenus, ReplyMenus, get_button_menu

# Keeping all global vars in one place
GLOBAL_CATEGORIES = []
ARROWS = {}

use_buttons = False
use_replies = True


def set_menu(*, replies, buttons, validate_buttons: bool = False):
    global use_replies
    global use_buttons

    if replies is not None:
        if replies:
            if dpy_version <= "1.5.0":
                return (
                    "You need to have discord.py version 1.6.0 or greater to use replies.",
                    False,
                )
            use_replies = True
            if buttons is None:
                return "Enabled replies for help menus.", True
        else:
            use_replies = False
            if buttons is None:
                return "Disabled replies for help menus.", True

    if buttons is not None:
        if buttons:
            if validate_buttons:
                try:
                    get_button_menu(use_replies)
                except RuntimeError as error:
                    return str(error), 0
            use_buttons = True
            return "Enabled buttons for help menus.", True
        else:
            use_buttons = False
            return "Disabled buttons for help menus.", True

    if buttons is False and replies is False:
        use_replies = False
        use_buttons = False
        return "Reset the help menu to vanilla.", True
    elif buttons is True and replies is True:
        return "Enabled replies and buttons for help menus.", True

    raise RuntimeError(f"unreachable code reached: replies={replies}, buttons={buttons}")


# wew thanks jack
def get_menu():
    global use_buttons
    global use_replies
    if use_buttons:
        try:
            return get_button_menu(use_replies)
        except RuntimeError:
            # User unloaded slashtags, so fallback to normal menu
            pass
    if use_replies:
        return ReplyMenus
    return NoReplyMenus
