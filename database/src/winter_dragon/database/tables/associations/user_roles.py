from sqlalchemy import Column, ForeignKey
from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.role import Roles
from winter_dragon.database.tables.user import Users


class UserRoles(SQLModel, table=True):
    role_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Roles)), primary_key=True))
    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users), ondelete="CASCADE"), primary_key=True))
