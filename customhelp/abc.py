class ThemesMeta:
    """This is the skeletal structure of any theme"""

    # Would need to work on this, to make the class look like an ABC ie:ABC but incomplete interfaces.
    # https://stackoverflow.com/questions/61328355/prohibit-addition-of-new-methods-to-a-python-child-class
    # No themes can have helper methods cause "self" changes during monkey-patch, making them obselete
    def __init_subclass__(cls, *args, **kw):
        super().__init_subclass__(*args, **kw)
        ALL_FEATURES = (
            "format_cog_help",
            "format_category_help",
            "format_bot_help",
            "format_command_help",
        )
        # By inspecting `cls.__dict__` we pick all methods declared directly on the class
        for name, attr in cls.__dict__.items():
            attr = getattr(cls, name)
            if not callable(attr) or name in ALL_FEATURES:
                continue
            else:
                # method not found in superclasses:
                raise TypeError(
                    f"Method {name} defined in {cls.__name__}  does not exist in superclasses"
                )


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
"""
