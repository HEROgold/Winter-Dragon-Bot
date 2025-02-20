from sqlmodel import Field, SQLModel

from database.tables.definitions import USERS_ID


class SyncBanUser(SQLModel, table=True):

    user_id: int = Field(foreign_key=USERS_ID, primary_key=True)
