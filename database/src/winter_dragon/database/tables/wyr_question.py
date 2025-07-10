from sqlalchemy import String
from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel


class WyrQuestion(SQLModel, table=True):
    value: str = Field(String())
