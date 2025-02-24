from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from database.tables.user import User


class Player(SQLModel, table=True):

    id = Field(foreign_key=User, primary_key=True)
    last_collection: datetime = Field(default=datetime.now(tz=UTC))
