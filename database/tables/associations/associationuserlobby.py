from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.constants import CASCADE
from database.tables.base import Base
from database.tables.definitions import LOBBIES_ID, USERS_ID


class AssociationUserLobby(SQLModel, table=True):

    lobby_id = 
    user_id: int = Field(foreign_key=USERS_ID)
