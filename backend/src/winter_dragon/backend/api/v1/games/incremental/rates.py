
from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.incremental.generators import Generators


class GeneratorRates(SQLModel, table=True):

    generator_id: int = Field(foreign_key=get_foreign_key(Generators, "id"), primary_key=True)
    currency: int
    per_second: int
