from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import MESSAGES_ID


class Hangman(SQLModel, table=True):

    id: int = Field(foreign_key=MESSAGES_ID, primary_key=True, unique=True)
    word: str
    letters: str
