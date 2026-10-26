"""The message a hangman game shows, and its Guess button."""

lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import ActionRow, Button, ButtonStyle

lazy from .models import MAX_WRONG_GUESSES, HangmanStatus


if TYPE_CHECKING:
    lazy from collections.abc import Sequence

    lazy from wd_bot.components import ComponentHandler

    lazy from .models import HangmanGame


GALLOWS = (
    ("      ", "      ", "      ", "      ", "      "),
    ("      ", "      ", "      ", "      ", "======"),
    ("  |   ", "  |   ", "  |   ", "  |   ", "======"),
    (" +--+ ", "  |   ", "  |   ", "  |   ", "======"),
    (" +--+ ", " |  | ", "  |   ", "  |   ", "======"),
    (" +--+ ", " |  | ", " O  | ", "  |   ", "======"),
    (" +--+ ", " |  | ", " O  | ", " |  | ", "======"),
    (" +--+ ", " |  | ", " O  | ", "/|  | ", "======"),
    (" +--+ ", " |  | ", " O  | ", r"/|\ | ", "======"),
    (" +--+ ", " |  | ", " O  | ", r"/|\ | ", "/ ====="),
    (" +--+ ", " |  | ", " O  | ", r"/|\ | ", r"/ \===="),
)
"""The drawing after 0 to 10 wrong guesses, one string per line."""


def drawing(wrong: int) -> str:
    """Return the gallows after ``wrong`` wrong guesses."""
    return "\n".join(GALLOWS[min(wrong, MAX_WRONG_GUESSES)])


def game_message(game: HangmanGame, participants: Sequence[int] = ()) -> str:
    """Return the text of the game's message: the drawing, the word so far, the wrong guesses and, once over, the result."""
    wrong = [*game.wrong_letters, *game.wrong_word_list]
    lives = MAX_WRONG_GUESSES - game.wrong_count
    lines = [
        f"```\n{drawing(game.wrong_count)}\n```",
        f"Word: `{game.masked}`",
        f"Wrong: {', '.join(wrong) if wrong else 'none'}",
    ]
    match game.status:
        case HangmanStatus.ACTIVE:
            lines.append(f"Lives left: {lives}")
        case HangmanStatus.WON:
            credited = ", ".join(f"<@{user_id}>" for user_id in participants) or "nobody"
            lines.append(f"**You won!** The word was `{game.word}`. Credited: {credited}")
        case HangmanStatus.LOST:
            lines.append(f"**You lost.** The word was `{game.word}`.")
    return "\n".join(lines)


def guess_buttons(guess_button: ComponentHandler, game: HangmanGame) -> list[ActionRow]:
    """Return the row holding the Guess button of ``game``; none once the game is over."""
    if game.status is not HangmanStatus.ACTIVE:
        return []
    if game.id is None:
        msg = "A game must be stored before it gets a Guess button."
        raise ValueError(msg)
    button = Button(style=ButtonStyle.PRIMARY, label="Guess", custom_id=guess_button.custom_id(game.id))
    return [ActionRow(components=[button])]
