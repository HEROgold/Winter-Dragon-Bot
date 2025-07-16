
from winter_dragon.database.extension.model import SQLModel


class Commands(SQLModel, table=True):

    qual_name: str
    call_count: int
