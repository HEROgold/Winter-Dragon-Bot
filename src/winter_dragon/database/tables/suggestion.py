from __future__ import annotations

from typing import TYPE_CHECKING

from winter_dragon.database.extension.model import SQLModel


if TYPE_CHECKING:
    from datetime import datetime


class Suggestions(SQLModel, table=True):
    type: str
    verified_at: datetime | None = None
    content: str
