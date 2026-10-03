"""Unit tests: the diff-based command sync engine (no network, no real Discord calls)."""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy import pytest
lazy from sqlalchemy import BigInteger
lazy from sqlalchemy.ext.compiler import compiles
lazy from sqlmodel import Session, SQLModel, create_engine
lazy from wd_bot.auto_sync import CommandRecord, GlobalSyncedCommand, diff_global_commands


if TYPE_CHECKING:
    lazy from collections.abc import Generator


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite.

    wd_db's SQLModel.id is a BigInteger primary key, which sqlite only autoincrements when the
    column type is exactly INTEGER. Postgres (production) is unaffected.
    """
    return "INTEGER"


@dataclass
class FakeCommand:
    name: str
    _signature: str

    def signature(self) -> str:
        return self._signature


@pytest.fixture
def session() -> Generator[Session]:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_new_command_is_created(session: Session) -> None:
    plan = diff_global_commands(session, [FakeCommand("percentage", "(user: User) -> None")])
    assert [c.name for c in plan.to_create] == ["percentage"]
    assert plan.to_edit == []
    assert plan.to_delete == []


def test_unchanged_signature_does_nothing(session: Session) -> None:
    record = CommandRecord(name="percentage")
    session.add(record)
    session.commit()
    session.refresh(record)
    session.add(GlobalSyncedCommand(command_id=record.id, signature="(user: User) -> None", discord_command_id="10"))
    session.commit()

    plan = diff_global_commands(session, [FakeCommand("percentage", "(user: User) -> None")])
    assert plan.to_create == []
    assert plan.to_edit == []
    assert plan.to_delete == []


def test_changed_signature_is_edited(session: Session) -> None:
    record = CommandRecord(name="percentage")
    session.add(record)
    session.commit()
    session.refresh(record)
    session.add(GlobalSyncedCommand(command_id=record.id, signature="(user: User) -> None", discord_command_id="10"))
    session.commit()

    plan = diff_global_commands(session, [FakeCommand("percentage", "(user: User, extra: int) -> None")])
    assert plan.to_create == []
    assert [(c.name, discord_id) for c, discord_id in plan.to_edit] == [("percentage", "10")]
    assert plan.to_delete == []


def test_removed_command_is_deleted(session: Session) -> None:
    record = CommandRecord(name="old")
    session.add(record)
    session.commit()
    session.refresh(record)
    session.add(GlobalSyncedCommand(command_id=record.id, signature="() -> None", discord_command_id="20"))
    session.commit()

    plan = diff_global_commands(session, [])
    assert plan.to_create == []
    assert plan.to_edit == []
    assert plan.to_delete == ["20"]
