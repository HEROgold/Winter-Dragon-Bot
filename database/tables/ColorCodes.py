from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.Base import Base
from database.tables.definitions import GUILDS_ID


class ColorCodes(Base):
    __tablename__ = "color_codes"

    id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True, unique=True, autoincrement=False)
    created_color: Mapped[int] = mapped_column(Integer(), default=0x00FF00)
    changed_color: Mapped[int] = mapped_column(Integer(), default=0xFFFF00)
    deleted_color: Mapped[int] = mapped_column(Integer(), default=0xFF0000)
