from sqlalchemy import String
from sqlmodel import Field, SQLModel


class WyrQuestion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    value: str = Field(String())
