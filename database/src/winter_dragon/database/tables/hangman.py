from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.message import Messages


class Hangmen(SQLModel, table=True):

    message_id: int = Field(foreign_key=get_foreign_key(Messages, "id"), primary_key=True)
    word: str
    letters: str
