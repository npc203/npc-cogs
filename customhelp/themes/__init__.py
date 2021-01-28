from . import dank, danny, justcore, minimalhelp, nadeko, twin
from inspect import isclass
from pkgutil import iter_modules
from importlib import import_module
import os


# TODO automate the generation of this list
list = {
    "danny": danny.DannyHelp,
    "dank": dank.DankHelp,
    "minimal": minimalhelp.MinimalHelp,
    "nadeko": nadeko.NadekoHelp,
    "justcore": justcore.JustCore,
    "twin": twin.TwinHelp,
}

"""
pkg_dir = os.path.dirname(__file__)

for (module_loader, name, ispkg) in iter_modules([pkg_dir]):
    theme_module = import_module(f"{__name__}.{name}")
    for attribute in dir(theme_module):
        attr = getattr(theme_module, attribute)
        if isclass(attr):
            print(attribute)
"""