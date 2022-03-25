from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from customhelp.core.category import Arrow


class ArrowManager:
    def __init__(self):
        self.arrows: List[Arrow] = []

    def append(self, arrow):
        self.arrows.append(arrow)

    def clear(self):
        self.arrows.clear()

    def __getitem__(self, name: str):
        for arrow in self.arrows:
            if arrow.name == name:
                return arrow
        raise RuntimeError(f"No arrow with name {name}")

    def __iter__(self):
        return iter(self.arrows)


# Keeping all global vars in one place
GLOBAL_CATEGORIES = []
ARROWS = ArrowManager()
