
from datetime import datetime

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class CarFuels(SQLModel, table=True):

    user_id: int = Field(foreign_key=get_foreign_key(Users), ondelete="CASCADE")
    amount: int
    distance: int
    price: int
    timestamp: datetime = Field(default_factory=datetime.now)
