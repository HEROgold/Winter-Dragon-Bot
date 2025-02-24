
from sqlmodel import Relationship, SQLModel

from database.tables.definitions import AUTO_INCREMENT_ID


class Command(SQLModel, table=True):

    id = AUTO_INCREMENT_ID # Test if this works as a primary key. Test if it works on different tables.
    qual_name: str
    call_count: int

    parent = Relationship(back_populates="children", link_model="Command")
    children = Relationship(back_populates="parent", link_model="Command")
