from typing import Self

from sqlmodel import Field, SQLModel, select

from database.tables.definitions import USERS_ID


class Infractions(SQLModel, table=True):

    user_id: int = Field(foreign_key=USERS_ID)
    infraction_count: int = Field(default=0)

    @classmethod
    def add_infraction_count(cls, user_id: int, amount: int) -> None:
        """Add an infraction to a user, if it isn't in this table add it."""
        from database import session

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
        from database import session

        with session:
            if user := session.exec(select(cls).where(cls.user_id == id_)).first():
                return user

            inst = cls(user_id=id_)
            session.add(inst)
            session.commit()
            return inst
