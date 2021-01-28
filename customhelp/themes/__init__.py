import os
from importlib import import_module
from inspect import isclass
from pkgutil import iter_modules

from ..abc import ThemesMeta

list = {}

# This auto populates the list with the themes present in this folder
pkg_dir = os.path.dirname(__file__)
for (module_loader, name, ispkg) in iter_modules([pkg_dir]):
    theme_module = import_module(f"{__name__}.{name}")
    for attribute in dir(theme_module):
        attr = getattr(theme_module, attribute)
        if isclass(attr) and issubclass(attr, ThemesMeta) and attr is not ThemesMeta:
            list[name] = attr
