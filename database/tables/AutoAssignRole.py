from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.constants import CASCADE
from database.tables.Base import Base
from database.tables.definitions import GUILDS_ID, ROLES_ID


class AutoAssignRole(Base):
    __tablename__ = "auto_assign"

    role_id: Mapped[int] = mapped_column(ForeignKey(ROLES_ID, ondelete=CASCADE), primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
