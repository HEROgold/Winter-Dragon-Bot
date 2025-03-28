
from sqlmodel import SQLModel


class GeneratorRates(SQLModel, table=True):

    generator_id: int
    currency: int
    per_second: int
