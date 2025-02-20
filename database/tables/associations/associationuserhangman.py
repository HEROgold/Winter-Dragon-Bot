from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables.base import Base
from database.tables.definitions import HANGMEN_ID, USERS_ID


class AssociationUserHangman(SQLModel, table=True):

    id = 
    hangman_id = 
    user_id: int = Field(foreign_key=USERS_ID)
    score = 
