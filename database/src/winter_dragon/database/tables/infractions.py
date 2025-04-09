from typing import Self

from sqlmodel import Field, SQLModel, select
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class Infractions(SQLModel, table=True):

    user_id: int = Field(foreign_key=get_foreign_key(Users, "id"), primary_key=True)
    infraction_count: int = Field(default=0)

    @classmethod
    def add_infraction_count(cls, user_id: int, amount: int) -> None:
        """Add an infraction to a user, if it isn't in this table add it."""
        from winter_dragon.database import session

        with session:
            infraction = session.exec(select(cls).where(cls.user_id == user_id)).first()

            if infraction is None:
                infraction = cls(user_id=user_id, infraction_count=0)
                session.add(infraction)

            infraction.infraction_count += amount
            session.commit()

    @classmethod
    def fetch_user(cls, id_: int) -> Self:
        """Find existing or create new user, and return it."""
        from winter_dragon.database import session

        with session:
            if user := session.exec(select(cls).where(cls.user_id == id_)).first():
                return user

            inst = cls(user_id=id_)
            session.add(inst)
            session.commit()
            return inst
