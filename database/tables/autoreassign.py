from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.constants import CASCADE
from database.tables.base import Base
from database.tables.definitions import ROLES_ID


class AutoReAssign(Base):
    __tablename__ = "auto_reassign"

    guild_id: Mapped[int] = mapped_column(ForeignKey(ROLES_ID, ondelete=CASCADE), primary_key=True)
