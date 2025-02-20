from sqlmodel import Field, SQLModel


class Guild(SQLModel, table=True):

    id: int = Field(primary_key=True, unique=True, default=None)
