from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import GAMES_NAME, USERS_ID


class ResultDuels(Base):
    __tablename__ = "results_1v1"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    game: Mapped[str] = mapped_column(ForeignKey(GAMES_NAME))
    player_1: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    player_2: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    winner: Mapped[int | None] = mapped_column(ForeignKey(USERS_ID))
    loser: Mapped[int | None] = mapped_column(ForeignKey(USERS_ID))
