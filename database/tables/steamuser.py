from sqlmodel import Field, SQLModel


class SteamUser(SQLModel, table=True):

    id: int = Field()
