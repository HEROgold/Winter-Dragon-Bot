from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.user import Users


class SteamUsers(SQLModel, table=True):

    id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users, "id"))))
