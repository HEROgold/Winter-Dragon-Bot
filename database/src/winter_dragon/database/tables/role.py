from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel


class Roles(SQLModel, table=True):

    id: int | None = Field(sa_column=Column(BigInteger(), primary_key=True), default=None)
    name: str
