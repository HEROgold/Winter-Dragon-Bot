from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables import CASCADE, Base
from database.tables.definitions import GUILD_ID, ROLE_ID, USER_ID
from database.tables.guilds import Guild  # noqa: TCH001
from database.tables.users import User  # noqa: TCH001


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String)


class UserRoles(Base):
    __tablename__ = "user_roles"

    role_id: Mapped["Role"] = mapped_column(ForeignKey(ROLE_ID, ondelete=CASCADE), primary_key=True)
    guild_id: Mapped["Guild"] = mapped_column(ForeignKey(GUILD_ID), primary_key=True)
    user_id: Mapped["User"] = mapped_column(ForeignKey(USER_ID), primary_key=True)


class AutoAssignRole(Base):
    __tablename__ = "auto_assign"

    role_id: Mapped["Role"] = mapped_column(ForeignKey(ROLE_ID, ondelete=CASCADE), primary_key=True)
    guild_id: Mapped["Guild"] = mapped_column(ForeignKey(GUILD_ID), primary_key=True)


