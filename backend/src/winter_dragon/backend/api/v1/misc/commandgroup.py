from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel


class CommandGroups(SQLModel, table=True):

    id: int | None = Field(sa_column=Column(Numeric(20, 0), primary_key=True), default=None)
    name: str
