from datetime import UTC, datetime
from functools import partial

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship, func, select
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.user import Users


class AssociationUserCommand(SQLModel, table=True):

    timestamp: datetime = Field(default_factory=partial(datetime.now, tz=UTC), primary_key=True)
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users, "id"))))
    command_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Commands, "id"))))

    user: Users = Relationship()
    command: Commands = Relationship()

    @classmethod
    def cleanup(cls) -> None:  # sourcery skip: remove-unreachable-code
        """Clean the database to keep track of (at most) 1k commands for each user."""
        msg = "This method requires rewrite."
        raise NotImplementedError(msg)
        from winter_dragon.database import session

        track_amount = 1000
        with session:
            session.exec(
                select(cls.user_id)
                .group_by(cls.user_id)
                .having(func.count(cls.user_id) > track_amount)
                .delete(),
            ).all()
            session.commit()
