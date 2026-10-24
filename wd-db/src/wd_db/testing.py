"""Test helpers for code built on wd-db: an in-memory sqlite database standing in for PostgreSQL.

Importing this module makes sqlite render ``BigInteger`` as ``INTEGER``: wd-db's primary keys are ``BigInteger``,
and sqlite only autoincrements a column whose type is exactly ``INTEGER``. PostgreSQL is unaffected::

    engine = sqlite_engine()
    (reminder_id,) = seed(engine, Reminder(content="feed the cat", user_id=3, timestamp=now))
"""

from typing import TYPE_CHECKING, cast

from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
lazy from sqlalchemy import create_engine, event
lazy from sqlalchemy.orm import object_mapper
lazy from sqlalchemy.pool import StaticPool
lazy from sqlmodel import Session, SQLModel


if TYPE_CHECKING:
    lazy import sqlite3

    lazy from sqlalchemy import Engine
    lazy from sqlalchemy.engine.interfaces import DBAPIConnection
    lazy from sqlalchemy.pool import ConnectionPoolEntry


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite, so BigInteger primary keys autoincrement."""
    return "INTEGER"


def sqlite_engine(*, tables: bool = True, foreign_keys: bool = False) -> Engine:
    """Return a fresh in-memory database, shared across threads, with every registered table when ``tables``.

    Transactions are real (``autocommit=False``), so savepoints roll back as they do on PostgreSQL. With
    ``foreign_keys``, sqlite enforces foreign keys as PostgreSQL does; it ignores them by default.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False, "autocommit": False},
        poolclass=StaticPool,
    )
    if foreign_keys:

        @event.listens_for(engine, "connect")
        def _enforce_foreign_keys(connection: DBAPIConnection, _: ConnectionPoolEntry) -> None:
            # sqlite ignores this pragma inside a transaction, and with autocommit=False one is always open.
            sqlite = cast("sqlite3.Connection", connection)
            sqlite.autocommit = True
            sqlite.execute("PRAGMA foreign_keys=ON")
            sqlite.autocommit = False

    if tables:
        SQLModel.metadata.create_all(engine)
    return engine


def seed(engine: Engine, *rows: SQLModel) -> list[int]:
    """Store ``rows`` in one transaction and return their primary keys, in order."""
    with Session(engine) as session:
        session.add_all(rows)
        session.commit()
        return [object_mapper(row).primary_key_from_instance(row)[0] for row in rows]
