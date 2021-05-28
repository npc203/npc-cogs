class Game:
    def __init__(self, mode: bool):
        self.mode = mode  # True = normal mode, else reverse
        self.board = [[0 for _ in range(3)] for _ in range(3)]

    def move(self, pos, sign):
        self.board[pos[0]][pos[1]] = sign
        # return (is_ended,Message or None)
