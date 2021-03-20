import random

"""
none = 0
fruit = 1
head = 2
body = 3
"""


def get_point(size, board):
    """Returns x,y in board which is empty,else None"""
    i = 0
    # A max try of 20 chances
    for _ in range(20):
        x = random.randint(0, size - 1)
        y = random.randint(0, size - 1)
        if board[x][y] == 0:
            return x, y
    # At the worst case, try to traverse the board linearlly
    for i in range(size):
        for j in range(size):
            if board[i][j] == 0:
                return i, j


class Game:
    def __init__(self, size):
        self.size = size
        self.board = [[0 for i in range(size)] for j in range(size)]
        self.snake = [get_point(size - 2, self.board)]
        self.snake.append(self.snake[0])
        self.snake[1] = (self.snake[1][0], self.snake[1][1] - 1)
        self.board[self.snake[0][0]][self.snake[0][1]] = 2
        self.score = 1
        self.stop = False
        self.prev_fruit = None
        self.make_fruit()

    def move(self, m):
        mapper = {
            "w": (True, self.snake[0][0] - 1),
            "s": (True, self.snake[0][0] + 1),
            "a": (False, self.snake[0][1] - 1),
            "d": (False, self.snake[0][1] + 1),
        }
        if self.process_move(*mapper[m]):
            self.board[self.snake[0][0]][self.snake[0][1]] = 2
            self.board[self.snake[1][0]][self.snake[1][1]] = 3
            return True

    def make_fruit(self):
        if fruit := get_point(self.size, self.board):
            self.board[fruit[0]][fruit[1]] = 1
            if self.prev_fruit:
                self.board[self.prev_fruit[0]][self.prev_fruit[1]] = 0
            self.prev_fruit = fruit
            return True

    def process_move(self, x_or_y: bool, new: int):
        """Check death, increment score, return True or False
        If x_or_y is true then the player moved x, else y"""

        # TODO support going through walls a lil later
        if new >= self.size or new < 0:
            return False
        if x_or_y:
            # Empty block ahead
            if self.board[new][self.snake[0][1]] == 0:
                self.snake.insert(0, [new, self.snake[0][1]])
                rm = self.snake.pop(-1)
                self.board[rm[0]][rm[1]] = 0
                return True
            # User eats the fruit
            elif self.board[new][self.snake[0][1]] == 1:
                self.snake.insert(0, [new, self.snake[0][1]])
                self.score += 1
                if self.make_fruit():
                    return True
        else:
            if self.board[self.snake[0][0]][new] == 0:
                self.snake.insert(0, [self.snake[0][0], new])
                rm = self.snake.pop(-1)
                self.board[rm[0]][rm[1]] = 0
                return True
            elif self.board[self.snake[0][0]][new] == 1:
                self.snake.insert(0, [self.snake[0][0], new])
                self.score += 1
                if self.make_fruit():
                    return True
        return False
