"""Making sure a model's tables exist: the migrations own a database they manage, anything else is created on the spot.

A database the migrations manage holds :data:`MIGRATIONS_TABLE`. There a missing table means a model changed without
its migration, so :func:`ensure_tables` refuses rather than creating it: a table made on the spot would make the
migration that adds it fail later. Other databases (the sqlite test bot, tests) get the tables created directly.
"""

lazy from typing import TYPE_CHECKING

lazy from sqlalchemy import inspect
lazy from sqlmodel import SQLModel

lazy from wd_db.extension.lifecycle import LifecycleModel, ensure_lifecycle_columns


if TYPE_CHECKING:
    lazy from sqlalchemy import Connection, Engine


MIGRATIONS_TABLE = "alembic_version"
"""The table Alembic records the applied revision in; its presence marks a database the migrations manage."""


class UnmigratedTablesError(RuntimeError):
    """Tables a model defines are missing from a database the migrations manage."""

    def __init__(self, tables: list[str]) -> None:
        """Name the missing ``tables``."""
        super().__init__(
            f"Tables missing from the migrated database: {', '.join(tables)}. "
            "Add a migration for them and run `python -m winter_dragon.migrations upgrade`.",
        )
        self.tables = tables


def managed_by_migrations(bind: Engine | Connection) -> bool:
    """Return whether the migrations manage ``bind``'s database."""
    return inspect(bind).has_table(MIGRATIONS_TABLE)


def ensure_tables(bind: Engine | Connection, *models: type[SQLModel]) -> None:
    """Make sure the tables of ``models`` exist in ``bind``; each is named after its model, lowercased.

    In a database the migrations manage, raise :class:`UnmigratedTablesError` for any that don't. Elsewhere, create
    the missing ones; existing tables of lifecycle models gain the lifecycle columns an older bot didn't create.
    """
    tables = [SQLModel.metadata.tables[model.__name__.lower()] for model in models]
    if managed_by_migrations(bind):
        existing = set(inspect(bind).get_table_names())
        if missing := [table.name for table in tables if table.name not in existing]:
            raise UnmigratedTablesError(missing)
        return
    SQLModel.metadata.create_all(bind, tables=tables)
    ensure_lifecycle_columns(bind, *(model for model in models if issubclass(model, LifecycleModel)))
