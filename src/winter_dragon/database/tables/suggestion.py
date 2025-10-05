from datetime import datetime

from winter_dragon.database.extension.model import SQLModel


class Suggestions(SQLModel, table=True):

    type: str
    verified_at: datetime | None = None
    content: str
