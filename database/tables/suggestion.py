from sqlmodel import Field, SQLModel


class Suggestion(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    type: str
    is_verified: bool
    content: str
