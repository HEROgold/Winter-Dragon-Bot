
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import USERS_ID


class UserMoney(SQLModel, table=True):

    user_id: int = Field(foreign_key=USERS_ID)
    currency = 
    value = 
