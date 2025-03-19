
from pydantic import Field
from sqlmodel import Relationship, SQLModel


class Command(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    qual_name: str
    call_count: int

    parent = Relationship(back_populates="children", link_model="Command")
    children = Relationship(back_populates="parent", link_model="Command")
