from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.message import Messages


class Hangmen(SQLModel, table=True):

    id: int = Field(foreign_key=get_foreign_key(Messages, "id"), primary_key=True, unique=True)
    word: str
    letters: str
