"""Module for containing constants and configuration for the database package."""

from sqlalchemy import URL
from sqlmodel import Session, create_engine

from winter_dragon.config import Config


class DbUrl:
    """Class containing database URL components."""

    drivername = Config("postgresql")
    username = Config("postgres")
    password = Config("SECURE_PASSWORD")
    host = Config("postgres")
    port = Config(5432)
    database = Config("winter_dragon")


CASCADE = "CASCADE"
DATABASE_URL = URL.create(
    DbUrl.drivername,
    username=DbUrl.username,
    password=DbUrl.password,
    host=DbUrl.host,
    port=DbUrl.port,
    database=DbUrl.database,
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
