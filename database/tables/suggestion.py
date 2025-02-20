from sqlmodel import Field, SQLModel


class Suggestion(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    type: str = Field()
    is_verified: bool = Field()
    content: str = Field()
