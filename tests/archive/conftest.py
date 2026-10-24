"""Shared fixtures for the archive tests: an in-memory sqlite database with every archive table."""

from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_db.testing import sqlite_engine

import archive.models  # noqa: F401 - registers the archive's tables


if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine


@pytest.fixture
def engine() -> Engine:
    """Return a fresh in-memory database with every table created, usable from worker threads."""
    return sqlite_engine()


@pytest.fixture
def session(engine: Engine) -> Generator[Session]:
    """Return a session on the test database."""
    with Session(engine) as session:
        yield session
