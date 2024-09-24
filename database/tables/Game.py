from typing import Self

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.Base import Base
from tools.main_log import sql_logger as logger


class Game(Base):
    __tablename__ = "games"

    name: Mapped[str] = mapped_column(String(15), primary_key=True, unique=True)

    @classmethod
    def fetch_game_by_name(cls, name: str) -> Self:
        """Find existing or create new game, and return it

        Args:
            name (str): Name for the game
        """
        from database.session import session

        with session:
            logger.debug(f"Looking for game {name=}")
            if game := session.query(cls).where(cls.name == name).first():
                logger.debug(f"Returning game {name=}")
                return game

            logger.debug(f"Creating game {name=}")
            session.add(cls(name=name))
            session.commit()
            return session.query(cls).where(cls.name == name).first()  # type: ignore
