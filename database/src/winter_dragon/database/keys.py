

from sqlmodel import SQLModel


def get_foreign_key(table: type[SQLModel], column: str) -> str:
    """Get the foreign key for a given table and column."""
    return f"{table.__tablename__}.{column}"
