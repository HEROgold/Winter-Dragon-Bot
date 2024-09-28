
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base


class GeneratorRates(Base):
    __tablename__ = "incremental_rates"

    generator_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency: Mapped[int] = mapped_column(Integer, default=0)
    per_second: Mapped[int] = mapped_column(Integer, default=0)
