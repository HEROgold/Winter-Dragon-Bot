import logging
from typing import Literal


# from tools.config_reader import config

# See https://stackabuse.com/minimax-and-alpha-beta-pruning-in-python/ for guide.
# Look into alpha beta, min max.
Board = list[list[int]]


class TicTacToeAi:
    board: Board

    def __init__(self, o: int, x: int, board: Board = None) -> None:
        from .config import config
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.logger.debug("Getting TTT AI")
        self.board = (
            [[0, 0, 0],[0, 0, 0],[0, 0, 0]]
            if board is None
            else board
        )
        self.o = o
        self.x = x


    def get_button_location(self, row: int, column: int) -> int:
        self.logger.debug(f"Getting TTT AI button location at {row, column}!")
        return row*3 + column


    def get_best_move(self, player: int) -> tuple[int, int]:
        self.logger.debug("Getting best TTT AI move")
        target = -1 if player == self.x else 1

        _, coords = self.ttt_minimax(self.board, target=target)
        # (_, row, column) = self.max() if player == self.o else self.min()
        # (_, coords) = self.minimax(maximizer=True) if player == self.o else self.minimax(maximizer=False)
        if coords is not None:
            row, column = coords
        else:
            self.logger.critical(f"{coords=} not found")

        return row, column


    def available_moves(self, board: Board=None) -> Board:
        """Get the board state, with available coordinates."""
        moves = []
        if not board:
            board = self.board

        for i, row in enumerate(self.board):
            moves.extend([i, j] for j, column in enumerate(row) if column == 0)
        self.logger.debug(f"available {moves=}")
        return moves


    # Determines if the made move is a legal move
    def is_valid(self, row: int, column: int, board: Board) -> bool:
        if not board:
            board = self.board

        self.logger.debug(f"validating TTT move {row=}, {column=}")
        valid_coords = [0, 1, 2]
        return (
            row in valid_coords
            and column in valid_coords
            and board[row][column] == 0
        )


    def ttt_minimax(
        self,
        board_state: Board,
        last_move: tuple[int, int] = (None, None),
        target: int = -1,
    ) -> tuple[Literal[-1, 0,1], tuple[int, int]]:
        player = self.x if target == -1 else self.o

        available = self.available_moves(board_state)
        winner = self.check_winner(board_state)

        if (
            winner == target
            # winner in [target, 0] # Either win or draw. Should never lose.
            or not available
        ):
            self.logger.debug(f"Winner found at {target, last_move=}")
            self.winner = winner
            return winner, last_move

        # Set best score to worst at first iteration
        best_score = float("-inf") if target == 1 else float("inf")
        best_move = None, None

        for row, column in available:
            if not self.is_valid(row, column, board_state):
                self.logger.critical(f"Invalid move {last_move}, in {board_state} for {player}")
                msg = f"Invalid move {last_move}"
                raise ValueError(msg)

            board_state[row][column] = player
            l_score, l_move = self.ttt_minimax(board_state, last_move=(row, column), target=-target)
            board_state[row][column] = 0

            if l_score == target:
                # Best outcome
                self.logger.debug(f"best outcome at {l_score, l_move, board_state}")
                best_score = l_score
                best_move = l_move
                break
            if l_score == -target:
                self.logger.debug(f"loss at {l_score, l_move}")
                # Never expect a loss, keep searching

            best_score = l_score
            best_move = l_move
        return -best_score, best_move


    def check_horizontal(self, board: Board=None) -> Literal[-1, 1] | None:
        if not board:
            board = self.board

        for row in self.board:
            value = sum(row)
            if value == (self.x*3):
                return -1
            elif value == (self.o*3):  # noqa: RET505
                return 1
        return None


    def check_vertical(self, board: Board=None) -> Literal[-1, 1] | None:
        if not board:
            board = self.board

        for line in range(3):
            value = board[0][line] + board[1][line] + board[2][line]
            if value == (self.x*3):
                return -1
            elif value == (self.o*3):  # noqa: RET505
                return 1
        return None


    def check_diagonals(self, board: Board=None) -> Literal[-1, 1] | None:
        if not board:
            board = self.board

        diag = board[0][2] + board[1][1] + board[2][0] # /
        if diag == (self.x*3):
            return -1
        elif diag == (self.o*3):  # noqa: RET505
            return 1

        diag = board[0][0] + board[1][1] + board[2][2] # \
        if diag == (self.x*3):
            return -1
        elif diag == (self.o*3):  # noqa: RET505
            return 1
        return None


    def check_winner(self, board: Board=None) -> Literal[-1, 1, 0] | None:
        """Check winner: -1 for x, 0 for draw, 1 for o."""
        if not board:
            board = self.board

        horizontal = self.check_horizontal(board)
        vertical = self.check_vertical(board)
        diagonal = self.check_diagonals(board)

        for i in [horizontal, vertical, diagonal]:
            if i:
                return i

        # Check for empty spots, if filled, draw.
        if all(0 not in row for row in self.board):
            return 0

        self.logger.debug("Can't determine winner, board not filled yet")
        return None
