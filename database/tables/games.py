from typing import Self

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables import CASCADE, Base, session
from database.tables.definitions import GAME_NAME, LOBBY_STATUS, MESSAGE_ID, USER_ID
from tools.main_log import sql_logger as logger


class Hangman(Base):
    __tablename__ = "hangman"

    id: Mapped[int] = mapped_column(ForeignKey(MESSAGE_ID), primary_key=True, unique=True)
    word: Mapped[str] = mapped_column(String(24))
    letters: Mapped[str] = mapped_column(String(24), nullable=True)


class Game(Base):
    __tablename__ = "games"

    name: Mapped[str] = mapped_column(String(15), primary_key=True, unique=True)

    @classmethod
    def fetch_game_by_name(cls, name: str) -> Self:
        """Find existing or create new game, and return it

        Args:
            name (str): Name for the game
        """
        with session:
            logger.debug(f"Looking for game {name=}")
            if game := session.query(cls).where(cls.name == name).first():
                logger.debug(f"Returning game {name=}")
                return game

            logger.debug(f"Creating game {name=}")
            session.add(cls(name=name))
            session.commit()
            return session.query(cls).where(cls.name == name).first() # type: ignore


class LookingForGroup(Base):
    __tablename__ = "looking_for_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USER_ID))
    game_name: Mapped["Game"] = mapped_column(ForeignKey(GAME_NAME))


class ResultDuels(Base):
    __tablename__ = "results_1v1"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    game: Mapped["Game"] = mapped_column(ForeignKey(GAME_NAME))
    player_1: Mapped[int] = mapped_column(ForeignKey(USER_ID))
    player_2: Mapped[int] = mapped_column(ForeignKey(USER_ID))
    winner: Mapped[int | None] = mapped_column(ForeignKey(USER_ID))
    loser: Mapped[int | None] = mapped_column(ForeignKey(USER_ID))


class ResultMassiveMultiplayer(Base):
    __tablename__ = "results_mp"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    game: Mapped["Game"] = mapped_column(ForeignKey(GAME_NAME))
    user_id: Mapped[int] = mapped_column(ForeignKey(USER_ID))
    placement: Mapped[int | None] = mapped_column(nullable=True)


# TODO: convert to db enum
class LobbyStatus(Base):
    __tablename__ = "lobby_status"

    status: Mapped[str] = mapped_column(String(10), primary_key=True)

    @classmethod
    def create_default_values(cls) -> None:
        with session:
            for status in ["created", "waiting", "busy", "ended"]:
                if session.query(cls.status).where(cls.status == status).first():
                    continue
                session.add(cls(status=status))
            session.commit()

# Set up the default values for the lobby status table
LobbyStatus.create_default_values()


class Lobby(Base):
    __tablename__ = "lobbies"

    id: Mapped[int] = mapped_column(ForeignKey(MESSAGE_ID, ondelete=CASCADE), primary_key=True, unique=True)
    game: Mapped[str] = mapped_column(ForeignKey(GAME_NAME))
    status: Mapped[str] = mapped_column(ForeignKey(LOBBY_STATUS))


class WyrQuestion(Base):
    __tablename__ = "wyr_questions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    value: Mapped[str] = mapped_column(String())


class NhieQuestion(Base):
    __tablename__ = "nhie_questions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    value: Mapped[str] = mapped_column(String())
