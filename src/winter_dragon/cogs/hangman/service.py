"""The rules of hangman: starting a game, and what a guess does to it."""

lazy from enum import StrEnum
lazy from pathlib import Path
lazy from typing import TYPE_CHECKING

lazy from sqlmodel import col
lazy from wd_db.extension.lifecycle import alive, create_or_restore
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

lazy from .models import MAX_WRONG_GUESSES, HangmanGame, HangmanParticipant, HangmanStatus


if TYPE_CHECKING:
    lazy from random import Random

    lazy from sqlmodel import Session


WORDS_FILE = Path(__file__).parent / "words.txt"
"""The bundled word list: one lowercase word per line."""


class Guess(StrEnum):
    """What a guess did to a game."""

    CORRECT_LETTER = "correct letter"
    WRONG_LETTER = "wrong letter"
    CORRECT_WORD = "correct word"
    WRONG_WORD = "wrong word"


def load_words() -> list[str]:
    """Return the words of the bundled list."""
    return [word for word in WORDS_FILE.read_text(encoding="utf-8").split() if word]


def start_game(session: Session, *, guild_id: int, channel_id: int, rng: Random, words: list[str] | None = None) -> HangmanGame:
    """Store a new game in the channel with a word drawn from ``words`` (default: the bundled list)."""
    game = HangmanGame(guild_id=guild_id, channel_id=channel_id, word=rng.choice(words or load_words()))
    session.add(game)
    session.flush()
    return game


def parse_guess(text: str) -> str:
    """Return ``text`` as a guess: a single letter or a whole word, lowercase; refuse anything else."""
    guess = text.strip().casefold()
    if not guess or not guess.isalpha():
        msg = "Guess one letter, or the whole word. Use letters only."
        raise Refused(msg)
    return guess


def guess(session: Session, game: HangmanGame, user_id: int, text: str) -> Guess:
    """Apply ``text`` (one letter or the whole word) from ``user_id`` to ``game``; the caller commits.

    A wrong letter and a wrong word each cost one life. Repeating a guess refuses and costs nothing. The member
    becomes a Participant by guessing a correct letter, or the word. The game ends when the word is complete
    (won) or the lives run out (lost).
    """
    if game.status is not HangmanStatus.ACTIVE:
        msg = "This game is over."
        raise Refused(msg)
    attempt = parse_guess(text)
    result = _guess_letter(game, attempt) if len(attempt) == 1 else _guess_word(game, attempt)
    if result in {Guess.CORRECT_LETTER, Guess.CORRECT_WORD}:
        _add_participant(session, game, user_id)
    if game.solved:
        _finish(game, HangmanStatus.WON)
    elif game.wrong_count >= MAX_WRONG_GUESSES:
        _finish(game, HangmanStatus.LOST)
    session.add(game)
    return result


def _guess_letter(game: HangmanGame, letter: str) -> Guess:
    if letter in game.letters:
        msg = f"The letter {letter} was already guessed."
        raise Refused(msg)
    game.letters += letter
    return Guess.CORRECT_LETTER if letter in game.word else Guess.WRONG_LETTER


def _guess_word(game: HangmanGame, word: str) -> Guess:
    if word == game.word:
        game.letters += "".join(letter for letter in dict.fromkeys(game.word) if letter not in game.letters)
        return Guess.CORRECT_WORD
    if word in game.wrong_word_list:
        msg = f"The word {word} was already guessed."
        raise Refused(msg)
    game.wrong_words = ",".join([*game.wrong_word_list, word])
    return Guess.WRONG_WORD


def _add_participant(session: Session, game: HangmanGame, user_id: int) -> None:
    if game.id is None:
        msg = "A game must be stored before it is guessed at."
        raise ValueError(msg)
    same = HangmanParticipant.game_id == game.id, HangmanParticipant.user_id == user_id
    existing = session.exec(alive(HangmanParticipant).where(*same)).first()
    if existing is None:
        create_or_restore(session, HangmanParticipant(game_id=game.id, user_id=user_id))


def _finish(game: HangmanGame, status: HangmanStatus) -> None:
    game.status = status
    game.finished_at = utc_now()


def participants_of(session: Session, game: HangmanGame) -> list[int]:
    """Return the IDs of the members who took part in ``game``, in the order they joined."""
    rows = session.exec(
        alive(HangmanParticipant).where(HangmanParticipant.game_id == game.id).order_by(col(HangmanParticipant.id)),
    )
    return [row.user_id for row in rows]
