
from datetime import datetime

from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class CarFuels(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key=get_foreign_key(Users, "id"))
    amount: int
    distance: int
    price: int
    timestamp: datetime = Field(default_factory=datetime.now)
