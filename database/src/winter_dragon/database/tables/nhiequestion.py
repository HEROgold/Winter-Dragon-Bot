from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel


class NhieQuestion(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    value: str
