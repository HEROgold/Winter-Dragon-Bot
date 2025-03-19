from sqlalchemy import func
from sqlmodel import Field, SQLModel, select

from database.tables.definitions import COMMANDS_ID, USERS_ID


class AssociationUserCommand(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key=USERS_ID)
    command_id = Field(foreign_key=COMMANDS_ID)

    @classmethod
    def cleanup(cls) -> None:  # sourcery skip: remove-unreachable-code
        """Clean the database to keep track of (at most) 1k commands for each user."""
        msg = "This method requires rewrite."
        raise NotImplementedError(msg)
        from database import session

        track_amount = 1000
        with session:
            session.exec(
                select(cls.user_id)
                .group_by(cls.user_id)
                .having(func.count(cls.user_id) > track_amount)
                .delete(),
            ).all()
            session.commit()
