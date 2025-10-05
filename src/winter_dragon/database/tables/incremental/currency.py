
from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class UserMoney(SQLModel, table=True):

    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE", primary_key=True)
    currency: str = Field(primary_key=True)
    value: int = Field(default=0)
