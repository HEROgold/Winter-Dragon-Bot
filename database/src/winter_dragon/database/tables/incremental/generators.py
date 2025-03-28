
from sqlmodel import Field, SQLModel
from winter_dragon.database.tables.definitions import GENERATORS_ID, USERS_ID


class UserGenerator(SQLModel, table=True):

    id: int = Field(foreign_key=USERS_ID)
    generator_id: int = Field(foreign_key=GENERATORS_ID)
    count: int = Field(default=0)

