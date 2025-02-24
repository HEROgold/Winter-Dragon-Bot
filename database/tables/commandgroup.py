
from sqlalchemy.orm import relationship
from sqlmodel import Field, SQLModel


class CommandGroup(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    name: str

    commands = relationship(back_populates="parent")
