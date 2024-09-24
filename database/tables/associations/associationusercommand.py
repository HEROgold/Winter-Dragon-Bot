from sqlalchemy import ForeignKey
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
        """
        cleanup this database to keep track of (at most)
        1k commands for each user
        TODO: test
        TODO: Use sqlalchemy queries, as it's faster.
        """
        from database import session

        track_amount = 1000
        with session:
            data = session.query(cls).all()
            seen_users = []
            for row in data:
                seen_users.append(row.user_id)
                if seen_users.count(row.user_id) >= track_amount:
                    # get first findable row, then delete it
                    session.delete(session.query(cls).where(cls.user_id == row.user_id).first())
                    seen_users.remove(row.user_id)
            session.commit()
