from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
