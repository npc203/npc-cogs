from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from customhelp.core.category import Arrow, Category


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


class CategoryManager:
    def __init__(self) -> None:
        self._list: List[Category] = []

    @property
    def uncategorised(self):
        for category in self._list:
            if category.is_uncat:
                return category
        raise RuntimeError("Uncategorised category not set!")

    def get(self, name):
        return self._list[self.index(name)]

    # TODO remove redundant methods
    def clear(self):
        self._list.clear()

    def index(self, name):
        return self._list.index(name)

    def append(self, value):
        self._list.append(value)

    def __len__(self):
        return len(self._list)

    def __bool__(self):
        return bool(self._list)

    def __iter__(self):
        return iter(self._list)


# Keeping all global vars in one place
GLOBAL_CATEGORIES = CategoryManager()
ARROWS = ArrowManager()
