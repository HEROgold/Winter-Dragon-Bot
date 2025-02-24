
from sqlmodel import Field, SQLModel

from database.tables.definitions import GENERATORS_ID, USERS_ID


class UserGenerator(SQLModel, table=True):

    user_id: int = Field(foreign_key=USERS_ID)
    generator_id: int = Field(foreign_key=GENERATORS_ID)
    count: int

