from types import FunctionType

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.commands.help import HelpSettings

from .core.category import Category


class ThemesMeta:
    """This is the skeletal structure of any theme"""
    # Enforcing messes up the loader (loads all themes even tho they aren't present). HOTFIX
    pass


"""
async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings):
    pass

async def format_category_help(self, ctx: Context, obj: Category, help_settings: HelpSettings):
    pass

async def format_bot_help(self, ctx: Context, help_settings: HelpSettings):
    pass

async def format_command_help(
    self, ctx: Context, obj: commands.Command, help_settings: HelpSettings
):
    pass

# https://stackoverflow.com/questions/61328355/prohibit-addition-of-new-methods-to-a-python-child-class
# No themes can have helper methods cause "self" changes during monkey-patch, making them obselete
def __init_subclass__(cls, *args, **kw):
    super().__init_subclass__(*args, **kw)

    for superclass in cls.__mro__[1:]:
        for name in detect_overridden(cls, superclass):
            delattr(superclass, name)

    # By inspecting `cls.__dict__` we pick all methods declared directly on the class
    for name, attr in cls.__dict__.items():
        attr = getattr(cls, name)
        if not callable(attr):
            continue
        for superclass in cls.__mro__[1:]:
            if name in dir(superclass):
                break
        else:
            # method not found in superclasses:
            raise TypeError(
                f"Method {name} defined in {cls.__name__}  does not exist in superclasses"
            )

def detect_overridden(cls, obj):
    common = obj.__dict__.keys() - cls.__dict__.keys()
    # diff = [m for m in cls.__dict__.keys() if m not in common]
    return [i for i in list(common) if not i.startswith("_")]
"""