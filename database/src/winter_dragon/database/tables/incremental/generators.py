
from sqlmodel import Field, SQLModel


class Generators(SQLModel, table=True):

    id: int = Field(primary_key=True)
    name: str
