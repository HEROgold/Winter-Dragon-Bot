from sqlmodel import SQLModel


class AutoChannelSettings(SQLModel, table=True):

    id: int
    channel_name: str
    channel_limit: int
