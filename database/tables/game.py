from typing import Self

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class Game(Base):
    __tablename__ = "games"

    name: Mapped[str] = mapped_column(String(64), primary_key=True, unique=True)

    @classmethod
    def fetch_game_by_name(cls, name: str) -> Self:
        """Find existing or create new game, and return it

        Args:
            name (str): Name for the game
        """
        from database import session

        with session:
            if game := session.query(cls).where(cls.name == name).first():
                return game

            inst = cls(name=name)
            session.add(inst)
            session.commit()
            return inst
