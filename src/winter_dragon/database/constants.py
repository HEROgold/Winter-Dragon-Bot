"""Module for containing constants and configuration for the database package."""

from sqlalchemy import URL
from sqlmodel import Session, create_engine


CASCADE = "CASCADE"
DATABASE_URL = URL.create(
    drivername="postgresql",
    username="postgres",
    password="fp9iAsd8ufy7p9UF)p98sduYfjOfd98y123!@3",  # noqa: S106
    host="postgres",
    port=5432,
    database="winter_dragon",
)
engine = create_engine(DATABASE_URL, echo=False)
session = Session(engine)


class SessionMixin:
    """Mixin class to provide a session for database operations."""

    session: Session

    def __init_subclass__(cls) -> None:
        """Initialize the subclass with a database session."""
        cls.session = Session(engine)

    def __del__(self) -> None:
        """Close the database session."""
        self.session.close()
