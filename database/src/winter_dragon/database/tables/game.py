from typing import Self

from sqlmodel import Field, SQLModel, select


class Games(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    @classmethod
    def fetch_game_by_name(cls, name: str) -> Self:
        """Find existing or create new game, and return it.

        Args:
        ----
            name (str): Name for the game

        """
        from winter_dragon.database import session

        with session:
            if game := session.exec(select(cls).where(cls.name == name)).first():
                return game

            inst = cls(name=name)
            session.add(inst)
            session.commit()
            return inst
