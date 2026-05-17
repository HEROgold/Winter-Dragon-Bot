

from wd_db.extension.model import SQLModel


class WyrQuestion(SQLModel, table=True):
    value: str
