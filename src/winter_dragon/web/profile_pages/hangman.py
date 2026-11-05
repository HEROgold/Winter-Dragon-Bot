"""The Profile's hangman page: games the member took part in, how many were won, and a history, newest first."""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, cast

lazy from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import alive, owned_by

lazy from winter_dragon.cogs.hangman.models import HangmanGame, HangmanParticipant, HangmanStatus
lazy from winter_dragon.web.profile import ProfileContext, profile_page


if TYPE_CHECKING:
    from datetime import datetime

    from sqlmodel.sql.expression import SelectOfScalar
    from wd_discord.snowflake import Snowflake


@dataclass(frozen=True)
class FinishedGame:
    """One finished game the member took part in."""

    word: str
    won: bool
    wrong_guesses: tuple[str, ...]
    """The wrong letters, then the wrong words, in the order they were stored."""
    finished: datetime


def _finished_games(member_id: Snowflake) -> SelectOfScalar[HangmanGame]:
    """Return a select of the finished games the member took part in, newest first."""
    participations = owned_by(HangmanParticipant, member=member_id).subquery()
    return (
        alive(HangmanGame)
        .join(participations, col(HangmanGame.id) == participations.c.game_id)
        .where(col(HangmanGame.status) != HangmanStatus.ACTIVE, col(HangmanGame.finished_at).is_not(None))
        .order_by(col(HangmanGame.finished_at).desc())
    )


def _played(context: ProfileContext) -> bool:
    """Whether the member took part in a finished game."""
    with Session(context.bind) as session:
        return session.exec(_finished_games(context.member_id).limit(1)).first() is not None


@profile_page(slug="hangman", title="Hangman", template="profile/hangman.html", used=_played)
def hangman(context: ProfileContext) -> dict[str, object]:
    """Return the hangman page's context: the finished games the member took part in, newest first, and their counts."""
    with Session(context.bind) as session:
        games = session.exec(_finished_games(context.member_id)).all()
        history = [
            FinishedGame(
                word=game.word,
                won=game.status is HangmanStatus.WON,
                wrong_guesses=(*game.wrong_letters, *game.wrong_word_list),
                finished=cast("datetime", game.finished_at).astimezone(context.zone),  # the query keeps finished games only
            )
            for game in games
        ]
    return {"history": history, "played": len(history), "won": sum(game.won for game in history)}
