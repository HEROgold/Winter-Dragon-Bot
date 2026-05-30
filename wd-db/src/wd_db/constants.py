"""Module for containing constants and configuration for the database package."""
from __future__ import annotations

from sqlalchemy import URL
from sqlmodel import Session, create_engine
from wd_config import Config


class DbUrl:
    """Class containing database URL components."""

    driver_name = Config("postgresql")
    database = Config("winter_dragon")
    username = Config("postgres")
    password = Config("SECURE_PASSWORD")
    host = Config("postgres")
    port = Config(5432)


CASCADE = "CASCADE"
DATABASE_URL = URL.create(
    DbUrl.driver_name,
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

    session: Session = session
