import logging
from typing import Literal

from tools.config_reader import config


# See https://stackabuse.com/minimax-and-alpha-beta-pruning-in-python/ for guide.
# Look into alpha beta, min max.



class TicTacToeAi:
    board: list[list[int, int, int]]

    def __init__(self, o: int, x: int, board = None) -> None:
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.logger.debug("Getting TTT AI")
        if board is None:
            self.board = [
                    [0, 0, 0],
                    [0, 0, 0],
                    [0, 0, 0],
                ]
        self.board = board
        self.o = o
        self.x = x


    def get_button_location(self, row: int, column: int) -> int:
        self.logger.debug(f"Getting TTT AI button location at {row, column}!")
        return row*3 + column


    def get_best_move(self, player: int) -> tuple[int, int]:
        self.logger.debug("Getting best TTT AI move")
        (_, row, column) = self.max() if player == self.o else self.min()
        self.logger.debug(f"{self.is_valid(row, column)=}")
        if self.is_valid(row, column):
            return row, column


    def available_moves(self) -> list[list[int]]:
        """Get the board state, with available coordinates"""
        moves = []
        for i, row in enumerate(self.board):
            moves.extend([i, j] for j, column in enumerate(row) if column == 0)
        self.logger.debug(f"available {moves=}")
        return moves


    # Determines if the made move is a legal move
    def is_valid(self, row: int, column: int) -> bool:
        self.logger.debug(f"validating TTT move {row=}, {column=}")
        valid = [0, 1, 2]
        if row not in valid or column not in valid:
            return False
        elif self.board[row][column] != 0:
            return False
        else:
            return True


    # Player 'O' is max
    def max(self, alpha: int = 2, beta: int = -2):
        self.logger.debug("Getting TTT Max!")
        self.logger.debug(f"{self.board=}")
        # Possible values for max_score are:
        # -1 - loss
        # 0  - a tie
        # 1  - win

        # We're initially setting it to -2 as -2 is worse than the worst case:
        max_score = -20

        final_max_row = None
        final_max_column = None

        result = self.check_winner()
        self.logger.debug(f"{result=}")
        if result == -1:
            return (-1, 0, 0)
        elif result == 1:
            return (1, 0, 0)
        elif result == 0:
            return (0, 0, 0)

        self.logger.debug(f"{max_score=}")
        for row, column in self.available_moves():
            self.logger.debug(f"max: {row=}, {column=}, {max_score=}")
            if self.board[row][column] == 0:
                # On the empty field player 'O' makes a move and calls Min
                # That's one branch of the game tree.
                self.board[row][column] = self.o
                (min, _, _) = self.min(alpha, beta)
                # Fixing the max_score value if needed
                if min > max_score:
                    max_score = min
                    final_max_row = row
                    final_max_column = column
                # Setting back the field to empty
                self.board[row][column] = 0

                if max_score >= alpha:
                    return (max_score, final_max_row, final_max_column)

                if max_score > beta:
                    beta = max_score

        return (max_score, final_max_row, final_max_column)


    # Player 'X' is min, in this case human
    def min(self, alpha: int = -2, beta: int = 2):
        self.logger.debug("Getting TTT Min!")
        self.logger.debug(f"{self.board=}")
        # Possible values for min_score are:
        # -1 - win
        # 0  - a tie
        # 1  - loss

        # We're initially setting it to 2 as 2 is worse than the worst case:
        min_score = 20

        final_min_row = None
        final_min_column = None

        result = self.check_winner()
        self.logger.debug(f"{result=}")
        if result == -1:
            return (-1, 0, 0)
        elif result == 1:
            return (1, 0, 0)
        elif result == 0:
            return (0, 0, 0)

        self.logger.debug(f"{min_score=}")
        for row, column in self.available_moves():
            self.logger.debug(f"min: {row=}, {column=}, {min_score=}")
            if self.board[row][column] == 0:
                self.board[row][column] = self.x
                (max, _, _) = self.max(alpha, beta)
                if max < min_score:
                    min_score = max
                    final_min_row = row
                    final_min_column = column
                self.board[row][column] = 0

                if min_score <= alpha:
                    return (min_score, final_min_row, final_min_column)

                if min_score < beta:
                    beta = min_score

        return (min_score, final_min_row, final_min_column)


    def check_winner(self) -> Literal[-1, 1, 0] | None:
        """
        Check winner,
        -1 for x,
        0 for draw,
        1 for o
        """
        # Check horizontal
        for row in self.board:
            value = sum(row)
            if value == (self.x*3):
                return -1
            elif value == (self.o*3):
                return 1

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == (self.x*3):
                return -1
            elif value == (self.o*3):
                return 1

        # Check diagonals
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0] # /
        if diag == (self.x*3):
            return -1
        elif diag == (self.o*3):
            return 1

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2] # \
        if diag == (self.x*3):
            return -1
        elif diag == (self.o*3):
            return 1

        # Check for empty spots, if filled, draw.
        for i, row in enumerate(self.board):
            for j, _ in enumerate(row):
                if self.board[i][j] == 0:
                    break
            else:
                continue
            break
        else:
            return 0
        
        return None
