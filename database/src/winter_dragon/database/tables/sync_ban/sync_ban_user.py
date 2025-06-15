from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class SyncBanUser(SQLModel, table=True):
    """Track users that have been banned in the sync ban feature."""

    user_id: int = Field(foreign_key=get_foreign_key(Users), primary_key=True)
