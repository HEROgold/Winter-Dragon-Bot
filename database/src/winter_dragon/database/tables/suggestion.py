from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel


class Suggestions(SQLModel, table=True):

    type: str
    is_verified: bool = Field(default=False)
    content: str
