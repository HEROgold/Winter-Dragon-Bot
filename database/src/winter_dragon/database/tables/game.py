from __future__ import annotations

from typing import Self

from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel, select


class Games(SQLModel, table=True):
    name: str = Field(unique=True, index=True)
    alias: Self | None = Field(default=None, foreign_key="games.name") # Alias for an already existing game.

    @classmethod
    def fetch_game_by_name(cls, name: str) -> Self:
        """Find existing or create new game, and return it.

        Args:
        ----
            name (str): Name for the game

        """
        from winter_dragon.database.constants import session

        with session:
            if game := session.exec(select(cls).where(cls.name == name)).first():
                return game.alias or game

            inst = cls(name=name)
            session.add(inst)
            session.commit()
            return inst
