from typing import Self

from sqlmodel import SQLModel, select


class User(SQLModel, table=True):

    id: int

    @classmethod
    def fetch_user(cls, id_: int) -> Self:
        """Find existing or create new user, and return it."""
        from database import session

        with session:
            if user := session.exec(select(cls).where(cls.id == id_)).first():
                return user

            inst = cls(id=id_)
            session.add(inst)
            session.commit()
            return inst
