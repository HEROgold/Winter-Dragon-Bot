from datetime import timedelta

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.incremental.generators import Generators

from .currency import UserMoney


class GeneratorRates(SQLModel, table=True):
    """Table for storing rates for generators per currency type."""

    id: int | None = Field(default=None, primary_key=True)
    generator_id: int = Field(foreign_key=get_foreign_key(Generators), ondelete="CASCADE")
    currency: int = Field(foreign_key=get_foreign_key(UserMoney), ondelete="CASCADE")
    amount: float = Field(default=1.0)
    per: timedelta = Field(default=timedelta(hours=1))
