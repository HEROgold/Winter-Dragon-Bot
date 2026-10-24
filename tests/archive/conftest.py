"""Shared fixtures for the archive tests: an in-memory sqlite database with every archive table."""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, Engine, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

import archive.models  # noqa: F401 - registers the archive's tables


if TYPE_CHECKING:
    from collections.abc import Generator


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite, so BigInteger primary keys autoincrement."""
    return "INTEGER"


@pytest.fixture
def engine() -> Engine:
    """Return a fresh in-memory database with every table created, usable from worker threads."""
    # autocommit=False makes sqlite3 open real transactions, so savepoints roll back like on PostgreSQL.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False, "autocommit": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine: Engine) -> Generator[Session]:
    """Return a session on the test database."""
    with Session(engine) as session:
        yield session
