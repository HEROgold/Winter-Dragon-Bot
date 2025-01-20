from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import GUILDS_ID, ROLES_ID


class GuildRoles(Base):
    __tablename__ = "guild_roles"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey(ROLES_ID), primary_key=True)
