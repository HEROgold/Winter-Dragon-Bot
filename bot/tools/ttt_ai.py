import itertools
from typing import Literal


type Board = list[list[int]]  # 3*3 grid
type Player = Literal[1, -1]  # Technically a discord.Member


class TicTacToeAI:
    def __init__(self, board: Board | None=None) -> None:
        self.board = (
            [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
            if board is None
            else board
        )

    def is_winner(self, player: Player) -> bool:
        for row in self.board:
            if sum(row) == player * 3:
                return True
        return next(
            (
                True
                for col in range(3)
                if sum(self.board[row][col] for row in range(3)) == player * 3
            ),
            sum(self.board[i][i] for i in range(3)) == player * 3
            or sum(self.board[i][2 - i] for i in range(3)) == player * 3,
        )

    def is_draw(self) -> bool:
        return all(self.board[row][col] != 0 for row in range(3) for col in range(3))

    def minimax(self, depth: int, is_maximizing: bool, alpha: float, beta: float) -> Literal[1, -1, 0] | float:  # noqa: C901
        if self.is_winner(1):
            return 1
        if self.is_winner(-1):
            return -1
        if self.is_draw():
            return 0

        if is_maximizing:
            max_eval = float("-inf")
            for row in range(3):
                for col in range(3):
                    if self.board[row][col] == 0:
                        self.board[row][col] = 1
                        evaluation = self.minimax(depth + 1, False, alpha, beta)
                        self.board[row][col] = 0
                        max_eval = max(max_eval, evaluation)
                        alpha = max(alpha, evaluation)
                        if beta <= alpha:
                            break
            return max_eval
        min_eval = float("inf")
        for row in range(3):
            for col in range(3):
                if self.board[row][col] == 0:
                    self.board[row][col] = -1
                    evaluation = self.minimax(depth + 1, True, alpha, beta)
                    self.board[row][col] = 0
                    min_eval = min(min_eval, evaluation)
                    beta = min(beta, evaluation)
                    if beta <= alpha:
                        break
        return min_eval

    def find_best_move(self) -> tuple[Literal[-1], Literal[-1]] | tuple[int, int]:
        best_val = float("-inf")
        best_move = (-1, -1)
        for row, col in itertools.product(range(3), range(3)):
            if self.board[row][col] == 0:
                self.board[row][col] = 1
                move_val = self.minimax(0, False, float("-inf"), float("inf"))
                self.board[row][col] = 0
                if move_val > best_val:
                    best_val = move_val
                    best_move = (row, col)
        return best_move

# Example usage, TODO: TEST
ttt_ai = TicTacToeAI()
best_move = ttt_ai.find_best_move()
