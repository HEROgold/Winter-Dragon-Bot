from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.role import Roles
from winter_dragon.database.tables.user import Users


class UserRoles(SQLModel, table=True):

    role_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Roles, "id")), primary_key=True))
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users, "id")), primary_key=True))

