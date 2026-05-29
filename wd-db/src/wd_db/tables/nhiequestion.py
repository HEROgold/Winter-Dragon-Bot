from __future__ import annotations

from wd_db.extension.model import SQLModel


class NhieQuestion(SQLModel, table=True):
    value: str
