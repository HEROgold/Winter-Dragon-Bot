"""A database the migrations manage must already have a model's tables; any other gets them created."""

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Field, SQLModel

from wd_db.schema import MIGRATIONS_TABLE, UnmigratedTablesError, ensure_tables
from wd_db.testing import sqlite_engine


class SchemaRow(SQLModel, table=True):
    """A table for these tests only."""

    id: int = Field(primary_key=True)


def test_unmanaged_database_gets_the_tables_created() -> None:
    engine = sqlite_engine(tables=False)

    ensure_tables(engine, SchemaRow)

    assert inspect(engine).has_table("schemarow")


def test_managed_database_refuses_a_missing_table() -> None:
    engine = sqlite_engine(tables=False)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE {MIGRATIONS_TABLE} (version_num VARCHAR(32) NOT NULL)"))

    with pytest.raises(UnmigratedTablesError) as refused:
        ensure_tables(engine, SchemaRow)

    assert refused.value.tables == ["schemarow"]
    assert not inspect(engine).has_table("schemarow")


def test_managed_database_with_the_table_passes() -> None:
    engine = sqlite_engine(tables=False)
    ensure_tables(engine, SchemaRow)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE {MIGRATIONS_TABLE} (version_num VARCHAR(32) NOT NULL)"))

    ensure_tables(engine, SchemaRow)
