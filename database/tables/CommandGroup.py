from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables.Base import Base


if TYPE_CHECKING:
    from database.tables.Command import Command


class CommandGroup(Base):
    __tablename__ = "command_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30))

    commands: Mapped[list["Command"]] = relationship(back_populates="parent")
