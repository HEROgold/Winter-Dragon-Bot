from typing import Self

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel, select
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class Infractions(SQLModel, table=True):
    user_id: int = Field(foreign_key=get_foreign_key(Users), primary_key=True)
    infraction_count: int = Field(default=0)

    @classmethod
    def add_infraction_count(cls, user_id: int, amount: int) -> None:
        """Add an infraction to a user, if it isn't in this table add it."""
        infraction = cls.session.exec(select(cls).where(cls.user_id == user_id)).first()

        if infraction is None:
            infraction = cls(user_id=user_id, infraction_count=0)
            cls.session.add(infraction)

        infraction.infraction_count += amount
        cls.session.commit()

    @classmethod
    def fetch_user(cls, id_: int) -> Self:
        """Find existing or create new user, and return it."""
        if user := cls.session.exec(select(cls).where(cls.user_id == id_)).first():
            return user

        inst = cls(user_id=id_)
        cls.session.add(inst)
        cls.session.commit()
        return inst
