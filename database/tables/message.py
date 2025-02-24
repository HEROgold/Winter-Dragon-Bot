from sqlmodel import Field, SQLModel

from database.tables.definitions import CHANNELS_ID, USERS_ID


class Message(SQLModel, table=True):

    id: int = Field(primary_key=True, unique=True)
    content: str
    user_id: int = Field(foreign_key=USERS_ID)
    channel_id: int = Field(foreign_key=CHANNELS_ID, nullable=True)
