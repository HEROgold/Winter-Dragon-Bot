from __future__ import annotations

from typing import Self

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel, select


class Games(SQLModel, table=True):
    name: str = Field(unique=True, index=True)
    alias: int | None = Field(default=None, foreign_key="games.id")  # Alias for an already existing game.

    @classmethod
    def fetch_game_by_name(cls, name: str) -> Self:
        """Find existing or create new game, and return it.

        Args:
        ----
            name (str): Name for the game

        """
        if game := cls.session.exec(select(cls).where(cls.name == name)).first():
            return cls.session.exec(select(cls).where(cls.name == game.alias)).first() or game

        inst = cls(name=name)
        cls.session.add(inst)
        cls.session.commit()
        cls.id: int  # type: ignore[reportIncompatibleVariableOverride]  # noqa: B032
        return inst
