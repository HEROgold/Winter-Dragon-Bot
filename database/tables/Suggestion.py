from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.Base import Base


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    type: Mapped[str] = mapped_column(String(50))
    is_verified: Mapped[bool] = mapped_column(Boolean)
    content: Mapped[str] = mapped_column(String(2048))
