from __future__ import annotations

from winter_dragon.database.extension.model import SQLModel


class WyrQuestion(SQLModel, table=True):
    value: str
