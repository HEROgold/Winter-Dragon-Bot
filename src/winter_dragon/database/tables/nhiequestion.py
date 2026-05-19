from __future__ import annotations

from winter_dragon.database.extension.model import SQLModel


class NhieQuestion(SQLModel, table=True):
    value: str
