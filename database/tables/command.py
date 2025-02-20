
from sqlalchemy.orm import relationship
from sqlmodel import Field, SQLModel

from database.tables.definitions import AUTO_INCREMENT_ID


class Command(SQLModel, table=True):

    id = AUTO_INCREMENT_ID # Test if this works as a primary key. Test if it works on different tables.
    qual_name: str = Field()
    call_count: int = Field()
    parent_id: int = Field()

    parent = relationship(back_populates="commands", foreign_keys=[parent_id])
