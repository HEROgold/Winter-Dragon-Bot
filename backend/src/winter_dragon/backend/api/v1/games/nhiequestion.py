from sqlmodel import Field, SQLModel


class NhieQuestion(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    value: str
