
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.Base import Base
from database.tables.definitions import GAMES_NAME, USERS_ID


class LookingForGroup(Base):
    __tablename__ = "looking_for_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    game_name: Mapped[str] = mapped_column(ForeignKey(GAMES_NAME))
