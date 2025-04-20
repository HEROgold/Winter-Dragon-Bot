from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel


class Guilds(SQLModel, table=True):

    id: int = Field(default=None, sa_column=Column(BigInteger(), primary_key=True))
