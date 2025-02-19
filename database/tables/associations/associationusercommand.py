from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import COMMANDS_ID, USERS_ID


class AssociationUserCommand(Base):
    __tablename__ = "association_user_command"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID))

    @classmethod
    def cleanup(cls) -> None:
        """Clean the database to keep track of (at most) 1k commands for each user."""
        from database import session

        track_amount = 1000
        with session:
            (
                session.query(cls.user_id)
                .group_by(cls.user_id)
                .having(func.count(cls.user_id) > track_amount)
                .delete()
            )
            session.commit()
