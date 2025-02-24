
from sqlmodel import Field, SQLModel

from database.tables.definitions import LOBBIES_ID, USERS_ID


class AssociationUserLobby(SQLModel, table=True):

    lobby_id: int = Field(foreign_key=LOBBIES_ID)
    user_id: int = Field(foreign_key=USERS_ID)
