from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String)
