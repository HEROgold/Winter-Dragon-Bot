"""Module for containing constants and configuration for the database package."""
from __future__ import annotations

lazy from sqlalchemy import URL
lazy from sqlmodel import Session, create_engine
lazy from wd_config.db import DbUrl


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
