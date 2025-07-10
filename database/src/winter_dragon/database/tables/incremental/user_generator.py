from sqlalchemy import Column, ForeignKey
from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.incremental.generators import Generators
from winter_dragon.database.tables.user import Users


class AssociationUserGenerator(SQLModel, table=True):

    user_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Users, "id")), primary_key=True))
    generator_id: int = Field(foreign_key=get_foreign_key(Generators, "id"), primary_key=True)
    count: int = Field(default=0)
