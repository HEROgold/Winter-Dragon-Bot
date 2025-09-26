
from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel


class Commands(SQLModel, table=True):

    qual_name: str = Field()
    call_count: int = Field()
