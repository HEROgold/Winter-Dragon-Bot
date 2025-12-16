from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.incremental.generators import Generators


class GeneratorRates(SQLModel, table=True):
    generator_id: int = Field(foreign_key=get_foreign_key(Generators), primary_key=True)
    currency: int
    per_second: int
