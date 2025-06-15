from typing import Self

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel, select


class Users(SQLModel, table=True):

    id: int = Field(default=None, sa_column=Column(BigInteger(), primary_key=True))

    @classmethod
    def fetch(cls, id_: int) -> Self:
        """Find existing or create new user, and return it."""
        from winter_dragon.database import session

        with session:
            if user := session.exec(select(cls).where(cls.id == id_)).first():
                return user

            inst = cls(id=id_)
            session.add(inst)
            session.commit()
            return inst
