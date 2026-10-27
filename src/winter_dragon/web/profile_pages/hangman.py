"""The Profile's hangman page: games the member took part in, how many were won, and a history, newest first."""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import alive, owned_by

lazy from winter_dragon.cogs.hangman.models import HangmanGame, HangmanParticipant, HangmanStatus
lazy from winter_dragon.web.profile import ProfileContext, profile_page


if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class FinishedGame:
    """One finished game the member took part in."""

    word: str
    won: bool
    wrong_guesses: tuple[str, ...]
    """The wrong letters, then the wrong words, in the order they were stored."""
    finished: datetime


@profile_page(slug="hangman", title="Hangman", template="profile/hangman.html")
def hangman(context: ProfileContext) -> dict[str, object]:
    """Return the hangman page's context: the finished games the member took part in, newest first, and their counts."""
    with Session(context.bind) as session:
        participations = owned_by(HangmanParticipant, member=context.member_id).subquery()
        games = session.exec(
            alive(HangmanGame)
            .join(participations, col(HangmanGame.id) == participations.c.game_id)
            .where(col(HangmanGame.status) != HangmanStatus.ACTIVE, col(HangmanGame.finished_at).is_not(None))
            .order_by(col(HangmanGame.finished_at).desc()),
        ).all()
        history = [
            FinishedGame(
                word=game.word,
                won=game.status is HangmanStatus.WON,
                wrong_guesses=(*game.wrong_letters, *game.wrong_word_list),
                finished=game.finished_at.astimezone(context.zone),
            )
            for game in games
            if game.finished_at is not None
        ]
    return {"history": history, "played": len(history), "won": sum(game.won for game in history)}
