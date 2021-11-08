# Keeping all global vars in one place
GLOBAL_CATEGORIES = []


class ArrowManager:
    def __init__(self):
        self.arrows = []

    def append(self, arrow):
        self.arrows.append(arrow)
    
    def clear(self):
        self.arrows.clear() 

    def __getitem__(self, index: str):
        for arrow in self.arrows:
            if arrow.name == index:
                return arrow
        raise RuntimeError(f"No arrow with name {index}")

    def __iter__(self):
        return iter(self.arrows)


ARROWS = ArrowManager()
