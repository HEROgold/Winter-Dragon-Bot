from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables import CASCADE, Base
from database.tables.definitions import GUILDS_ID, ROLES_ID, USERS_ID


if TYPE_CHECKING:
    from database.tables.guilds import Guild
    from database.tables.users import User


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String)


class UserRoles(Base):
    __tablename__ = "user_roles"

    role_id: Mapped["Role"] = mapped_column(ForeignKey(ROLES_ID, ondelete=CASCADE), primary_key=True)
    guild_id: Mapped["Guild"] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    user_id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID), primary_key=True)


class AutoAssignRole(Base):
    __tablename__ = "auto_assign"

    role_id: Mapped["Role"] = mapped_column(ForeignKey(ROLES_ID, ondelete=CASCADE), primary_key=True)
    guild_id: Mapped["Guild"] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)


