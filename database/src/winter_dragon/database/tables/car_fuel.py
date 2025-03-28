
from datetime import datetime

from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import USERS_ID


class CarFuel(SQLModel, table=True):

    user_id: int = Field(foreign_key=USERS_ID)
    amount: int
    distance: int
    price: int
    timestamp: datetime = Field(default_factory=datetime.now)
