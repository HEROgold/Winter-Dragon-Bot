from __future__ import annotations

from sqlalchemy import BigInteger
from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.message import Messages


class Hangmen(SQLModel, table=True):
    message_id: int = Field(sa_type=BigInteger, foreign_key=get_foreign_key(Messages), unique=True)
    word: str
    letters: str
