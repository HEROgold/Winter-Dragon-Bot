

from typing import TYPE_CHECKING

from wd_db.extension.model import SQLModel


from datetime import datetime


class Suggestions(SQLModel, table=True):
    type: str
    verified_at: datetime | None = None
    content: str
