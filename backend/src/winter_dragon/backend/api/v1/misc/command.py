from sqlmodel import Field, SQLModel


class Commands(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    qual_name: str
    call_count: int
