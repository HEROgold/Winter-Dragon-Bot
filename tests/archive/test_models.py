"""The archive tables follow the conventions the mapping relies on."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from archive import models
from archive.models import ArchiveChild


def archive_tables() -> list[type[SQLModel]]:
    return [table for name in models.__all__ if isinstance(table := getattr(models, name), type) and hasattr(table, "__table__")]


def test_every_table_is_prefixed_and_has_custom_data() -> None:
    for table in archive_tables():
        name = table.__tablename__
        assert name.startswith("archive_"), name
        assert f"{name}_custom_data" in SQLModel.metadata.tables, name


def test_children_are_child_tables() -> None:
    for table in archive_tables():
        for key, child in getattr(table, "children", {}).items():
            assert issubclass(child, ArchiveChild), (table, key)


def test_declared_renames_and_scalars_name_real_columns() -> None:
    for table in archive_tables():
        columns = table.__table__.columns
        for target in vars(table).get("renames", {}).values():
            assert target in columns, (table, target)
        if issubclass(table, ArchiveChild) and table.scalar != "value":
            assert table.scalar in columns, table


def test_a_member_is_unique_per_guild_and_user(session: Session) -> None:
    session.add(models.Member(guild_id=1, user_id=2))
    session.add(models.Member(guild_id=1, user_id=2))
    with pytest.raises(IntegrityError):
        session.flush()
