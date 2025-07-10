from winter_dragon.database.extension.model import SQLModel


class Generators(SQLModel, table=True):
    """Table for storing generator data."""

    name: str
