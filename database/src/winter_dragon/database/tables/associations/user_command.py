from datetime import UTC, datetime
from functools import partial

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship, func, select
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.user import Users


class AssociationUserCommand(SQLModel, table=True):

    timestamp: datetime = Field(default_factory=partial(datetime.now, tz=UTC), index=True)
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users), ondelete="CASCADE")))
    command_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Commands))))

    user: Users = Relationship()
    command: Commands = Relationship()

    @classmethod
    def cleanup(cls) -> None:
        """Clean the database to keep track of (at most) 1k commands for each user."""
        track_amount = 1000
        users = cls.session.exec(
            select(cls.user_id)
            .having(func.count() > track_amount),
        ).all()

        for user_id in users:
            known = cls.session.exec(
                select(cls)
                .where(cls.user_id == user_id)
                .order_by(cls.timestamp.desc())
                .limit(track_amount),
            ).all()

            for record in known:
                cls.session.delete(record)

        cls.session.commit()
