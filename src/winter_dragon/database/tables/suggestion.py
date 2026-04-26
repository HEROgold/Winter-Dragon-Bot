

from typing import TYPE_CHECKING

from winter_dragon.database.extension.model import SQLModel


from datetime import datetime


class Suggestions(SQLModel, table=True):
    type: str
    verified_at: datetime | None = None
    content: str
