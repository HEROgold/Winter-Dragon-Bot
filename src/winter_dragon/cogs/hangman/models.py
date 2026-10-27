"""The hangman tables: a game, and the members who took part in it."""

from datetime import datetime
lazy from enum import StrEnum
lazy from typing import ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import LifecycleModel, Ownership, Through


MAX_WRONG_GUESSES = 10
"""How many wrong letters and wrong words a game allows before it is lost."""


class HangmanStatus(StrEnum):
    """Where a hangman game is: still being guessed, or over with a result."""

    ACTIVE = "active"
    WON = "won"
    LOST = "lost"


class HangmanGame(LifecycleModel, table=True):
    """One hangman game in a channel, owned by its guild; it keeps its state while active and its result once over."""

    ownership: ClassVar[Ownership] = Ownership(guild="guild_id")

    guild_id: int = Field(sa_type=BigInteger, index=True)
    channel_id: int = Field(sa_type=BigInteger)
    word: str
    letters: str = ""
    """Every letter guessed so far, right or wrong, in the order guessed."""
    wrong_words: str = ""
    """The whole-word guesses that were wrong, separated by commas."""
    status: HangmanStatus = HangmanStatus.ACTIVE
    finished_at: datetime | None = Field(default=None, sa_type=AwareDateTime)

    @property
    def wrong_letters(self) -> str:
        """The guessed letters that are not in the word."""
        return "".join(letter for letter in self.letters if letter not in self.word)

    @property
    def wrong_word_list(self) -> list[str]:
        """The wrong whole-word guesses."""
        return self.wrong_words.split(",") if self.wrong_words else []

    @property
    def wrong_count(self) -> int:
        """How many lives the game has cost: wrong letters plus wrong words."""
        return len(self.wrong_letters) + len(self.wrong_word_list)

    @property
    def masked(self) -> str:
        """The word with the letters not guessed yet hidden as ``_``."""
        return " ".join(letter if letter in self.letters else "_" for letter in self.word)

    @property
    def solved(self) -> bool:
        """Whether every letter of the word was guessed."""
        return all(letter in self.letters for letter in self.word)


class HangmanParticipant(LifecycleModel, table=True):
    """A member who guessed a correct letter in a game; every Participant of a won game is credited."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id", through=Through("game_id", HangmanGame))
    natural_key: ClassVar[tuple[str, ...]] = ("game_id", "user_id")

    game_id: int = Field(foreign_key="hangmangame.id", sa_type=BigInteger, index=True)
    user_id: int = Field(sa_type=BigInteger)


HANGMAN_TABLES = (HangmanGame, HangmanParticipant)
