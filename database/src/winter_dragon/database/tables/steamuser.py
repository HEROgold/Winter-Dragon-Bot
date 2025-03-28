from sqlmodel import SQLModel


class SteamUser(SQLModel, table=True):

    id: int
