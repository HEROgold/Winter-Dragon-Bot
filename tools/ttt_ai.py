import logging
from typing import Literal

from tools.config_reader import config


# See https://stackabuse.com/minimax-and-alpha-beta-pruning-in-python/ for guide.
# Look into alpha beta, min max.


class TicTacToeAi:
    board: list[list[int]]

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

        # (_, row, column) = self.max() if player == self.o else self.min()
        (_, coords) = self.minimax(maximizer=True) if player == self.o else self.minimax(maximizer=False)
        if coords is not None:
            row, column = coords
        else:
            self.logger.critical(f"{coords=} not found")

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


    def check_winner(self, board: list[list[int]] = None) -> Literal[-1, 1, 0] | None:
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
        
        self.logger.debug("Can't determine winner, board not filled yet")
        return None


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


    def minimax(
        self,
        current: int = 0,
        depth: int = 10,
        maximizer: bool = True,
        best_move: tuple[int] = (None, None),
        best_score: float = None
    ) -> tuple[float, tuple[int, int]] | None:
        """
        Applies the minimax algorithm to determine the best move in a game.

        Args:
            self: The current instance of the class.
            current (int): The current depth of the search tree (default: 0).
            depth (int): The maximum depth to search in the tree (default: 10).
            maximizer (bool): Indicates whether the current player is the maximizer (default: True).
            score (int): The score of the current game state (default: 0).
            best_move (tuple[int]): The best move found so far (default: (None, None)).
            best_score (float): The best score found so far (default: None).

        Returns:
            tuple[int, tuple[int, int]] | None: The best score and move, or None if no move is available.

        Examples:
            ```python
            ai = TicTacToeAi()
            best_score, best_move = ai.minimax()
            print(f"Best score: {best_score}, Best move: {best_move}")
            ```
        """

        if best_score is None:
            best_score = float("-inf") if maximizer else int("inf")

        if current >= depth and depth != -1:
            return best_score, best_move

        # Max score is 1,
        # Min score is -1
        # Return early when already at best
        if (
            best_score == 1
            and maximizer
            or best_score == -1
            and not maximizer
        ):
            self.logger.debug(f"at best: {maximizer=}, {best_score=}")
            return best_score, best_move

        self.logger.debug(f"{current=}, {depth=}, {maximizer=}, {best_move=}, {best_score=}, \n{self.board=}")

        for row, column in self.available_moves():
            self.board[row][column] = self.o if maximizer else self.x
            if result := self.check_winner():
                if (
                    result >= best_score
                    and maximizer
                    or result <= best_score
                    and not maximizer
                ):
                    self.logger.debug(f"Updating best location to {row=}, {column=}, {result=}, {best_score=}")
                    best_score = result
                    best_move = (row, column)

            # inverse inf score before inverse-ing maximizer
            maximizer = not maximizer
            if maximizer and best_score == float("-inf"):
                best_score = float("inf")
            elif not maximizer and best_score == float("inf"):
                best_score = float("-inf")
            new_score, new_move = self.minimax(current+1, depth, maximizer, best_move, best_score)

            # if new_score is worse then best_score, skip
            if (
                new_score > best_score
                and  maximizer
                or new_score < best_score
                and not maximizer
            ):
                self.logger.debug(f"already better: {maximizer=}, {new_score=}, {best_score=}")
            else:
                best_score = new_score
                best_move = new_move
            
            self.board[row][column] = 0
        return best_score, best_move



### MS AI GENERATED:


import itertools

def minimax(board: list[list[int]], player: int, depth: int = 0) -> int:
    """
    Minimax algorithm for tic-tac-toe game.
    :param board: The current state of the game, represented as a list of lists of integers.
    :param player: The current player, either 1 or -1.
    :param depth: The current depth of the recursive call, used to determine the score of a draw.
    :return: The best score for the current player.
    """
    # Check if the game is over
    winner = check_winner(board)
    if winner != 0:
        return winner * player
    elif all(board[i][j] != 0 for i in range(3) for j in range(3)):
        return 0

    # Initialize the best score
    best_score = float('-inf') if player == 1 else float('inf')

    # Try all possible moves
    for i, j in itertools.product(range(3), range(3)):
        if board[i][j] == 0:
            # Make the move
            board[i][j] = player
            # Call minimax recursively
            score = -minimax(board, -player, depth + 1)
            # Undo the move
            board[i][j] = 0
            # Update the best score
            if (player == 1 and score > best_score) or (player == -1 and score < best_score):
                best_score = score

    return best_score



def check_winner(board: list[list[int]]) -> int:
    """
    Check if there is a winner in the tic-tac-toe game.
    :param board: The current state of the game, represented as a list of lists of integers.
    :return: The winner of the game, either 1, -1, or 0 if there is no winner yet.
    """
    # Check rows
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] and board[i][0] != 0:
            return board[i][0]

    # Check columns
    for j in range(3):
        if board[0][j] == board[1][j] == board[2][j] and board[0][j] != 0:
            return board[0][j]

    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2] and board[0][0] != 0:
        return board[0][0]
    if board[2][0] == board[1][1] == board[0][2] and board[2][0] != 0:
        return board[2][0]

    # No winner yet
    return 0

def make_move(board: list[list[int]], player: int) -> None:
    """
    Make a move for the given player using the minimax algorithm.
    :param board: The current state of the game, represented as a list of lists of integers.
    :param player: The current player, either 1 or -1.
    """
    # Initialize the best score and move
    best_score = float('-inf') if player == 1 else float('inf')
    best_moves = []

    # Try all possible moves
    for i, j in itertools.product(range(3), range(3)):
        if board[i][j] == 0:
            # Make the move
            board[i][j] = player
            # Call minimax recursively
            score = minimax(board, -player)
            # Undo the move
            board[i][j] = 0
            # Update the best score and move
            if (player == 1 and score > best_score) or (player == -1 and score < best_score):
                best_score = score
                best_moves = [(i, j)]
            elif score == best_score:
                best_moves.append((i, j))

    # Choose a random move among the best moves
    from random import choice
    i, j = choice(best_moves)
    board[i][j] = player

def print_board(board: list[list[int]]) -> None:
    """
    Print the current state of the tic-tac-toe game.
    :param board: The current state of the game, represented as a list of lists of integers.
    """
    for i in range(3):
        for j in range(3):
            if board[i][j] == 1:
                print('X', end=' ')
            elif board[i][j] == -1:
                print('O', end=' ')
            else:
                print(' ', end=' ')
            if j < 2:
                print('|', end=' ')
        print()
        if i < 2:
            print('———')

def play_game() -> None:
    """
    Play a game of tic-tac-toe against the AI.
    """
    # Initialize the game
    board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    player = 1

    # Play the game
    while True:
        # Print the current state of the game
        print_board(board)
        print()

        # Check if the game is over
        winner = check_winner(board)
        if winner == 1:
            print('X wins!')
            break
        elif winner == -1:
            print('O wins!')
            break
        elif all(board[i][j] != 0 for i in range(3) for j in range(3)):
            print('Draw!')
            break

        # Make a move
        if player == 1:
            while True:
                move = input('Enter your move (row column): ')
                i, j = map(int, move.split())
                if 0 <= i < 3 and 0 <= j < 3 and board[i][j] == 0:
                    board[i][j] = player
                    break
                else:
                    print('Invalid move!')
        else:
            make_move(board, player)

        # Switch players
        player = -player

if __name__ == '__main__':
    play_game()
