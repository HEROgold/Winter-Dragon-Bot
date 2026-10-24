"""Shared fixtures for the archive tests: an in-memory sqlite database with every archive table."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

import archive.models  # noqa: F401 - registers the archive's tables


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite, so BigInteger primary keys autoincrement."""
    return "INTEGER"


@pytest.fixture
def session() -> Generator[Session]:
    """Return a session on a fresh in-memory database with every table created."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
