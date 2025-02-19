from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import HANGMEN_ID, USERS_ID


class AssociationUserHangman(Base):
    __tablename__ = "association_users_hangman"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    hangman_id: Mapped[int] = mapped_column(ForeignKey(HANGMEN_ID))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    score: Mapped[int] = mapped_column(Integer, default=0)
