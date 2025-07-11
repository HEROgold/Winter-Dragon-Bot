from sqlmodel import Field, SQLModel


class Suggestions(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    type: str
    is_verified: bool = Field(default=False)
    content: str
