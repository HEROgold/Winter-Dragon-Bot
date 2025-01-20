from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import GAMES_NAME, USERS_ID


class ResultMassiveMultiplayer(Base):
    __tablename__ = "results_mp"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    game: Mapped[str] = mapped_column(ForeignKey(GAMES_NAME))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    placement: Mapped[int | None] = mapped_column(nullable=True)
