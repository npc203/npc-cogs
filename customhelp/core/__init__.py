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
        self._UNCAT_INDEX = -1

    def add_uncategorised(self, category):
        self._list.insert(self.UNCAT_INDEX, category)

    @property
    def UNCAT_INDEX(self):
        # if self._UNCAT_INDEX < 0:
        #     # Dev debug
        #     raise RuntimeError("Uncategorised category not set!")
        return self._UNCAT_INDEX

    @UNCAT_INDEX.setter
    def UNCAT_INDEX(self, value):
        self._UNCAT_INDEX = value

    @property
    def uncategorised(self):
        return self._list[self.UNCAT_INDEX]

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
