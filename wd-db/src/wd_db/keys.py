"""Module with helper methods for the database package."""

from sqlmodel import SQLModel


def get_foreign_key(table: type[SQLModel], column: str = "id") -> str:
    """Get the foreign key for a given table and column."""
    return f"{table.__tablename__}.{column}"
