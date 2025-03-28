
from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import USERS_ID


class UserMoney(SQLModel, table=True):

    id: int = Field(foreign_key=USERS_ID, primary_key=True)
    currency: str = Field(primary_key=True)
    value: int = Field(default=0)
