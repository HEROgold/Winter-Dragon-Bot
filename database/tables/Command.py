from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.tables.Base import Base
from database.tables.definitions import COMMAND_GROUPS_ID


if TYPE_CHECKING:
    from database.tables.CommandGroup import CommandGroup


class Command(Base):
    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    qual_name: Mapped[str] = mapped_column(String(30))
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_id: Mapped[int] = mapped_column(ForeignKey(COMMAND_GROUPS_ID), nullable=True)

    parent: Mapped["CommandGroup"] = relationship(back_populates="commands", foreign_keys=[parent_id])
