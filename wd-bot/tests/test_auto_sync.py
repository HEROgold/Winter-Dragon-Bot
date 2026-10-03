"""Unit tests: the diff-based command sync engine (no network, no real Discord calls)."""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy import pytest
lazy from sqlmodel import Session
lazy from wd_bot.auto_sync import (
    CommandRecord,
    GlobalSyncedCommand,
    GuildSyncedCommand,
    diff_global_commands,
    diff_guild_commands,
)


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from sqlalchemy import Engine



@dataclass
class FakeCommand:
    name: str
    _signature: str

    def signature(self) -> str:
        return self._signature


@pytest.fixture
def session(engine: Engine) -> Generator[Session]:
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


def _add_record(session: Session, name: str) -> int:
    record = CommandRecord(name=name)
    session.add(record)
    session.commit()
    session.refresh(record)
    assert record.id is not None
    return record.id


def _add_guild_row(session: Session, command_id: int, guild_id: int, signature: str, discord_id: str) -> None:
    session.add(
        GuildSyncedCommand(
            command_id=command_id,
            guild_id=guild_id,
            signature=signature,
            discord_command_id=discord_id,
        ),
    )
    session.commit()


def test_unsynced_record_live_is_created(session: Session) -> None:
    _add_record(session, "percentage")

    plan = diff_global_commands(session, [FakeCommand("percentage", "() -> None")])
    assert [c.name for c in plan.to_create] == ["percentage"]
    assert plan.to_edit == []
    assert plan.to_delete == []


def test_unsynced_record_not_live_does_nothing(session: Session) -> None:
    _add_record(session, "old")

    plan = diff_global_commands(session, [])
    assert plan.to_create == []
    assert plan.to_edit == []
    assert plan.to_delete == []


def test_guild_unchanged_signature_does_nothing_for_synced_guild(session: Session) -> None:
    _add_guild_row(session, _add_record(session, "percentage"), 1, "() -> None", "10")

    plan = diff_guild_commands(session, 1, [FakeCommand("percentage", "() -> None")])
    assert plan.to_create == []
    assert plan.to_edit == []
    assert plan.to_delete == []


def test_guild_row_for_other_guild_does_not_suppress_create(session: Session) -> None:
    _add_guild_row(session, _add_record(session, "percentage"), 1, "() -> None", "10")

    plan = diff_guild_commands(session, 2, [FakeCommand("percentage", "() -> None")])
    assert [c.name for c in plan.to_create] == ["percentage"]
    assert plan.to_edit == []
    assert plan.to_delete == []


def test_guild_changed_signature_is_edited_only_in_that_guild(session: Session) -> None:
    command_id = _add_record(session, "percentage")
    _add_guild_row(session, command_id, 1, "() -> None", "10")
    _add_guild_row(session, command_id, 2, "() -> None", "11")

    plan = diff_guild_commands(session, 2, [FakeCommand("percentage", "(x: int) -> None")])
    assert plan.to_create == []
    assert [(c.name, discord_id) for c, discord_id in plan.to_edit] == [("percentage", "11")]
    assert plan.to_delete == []


def test_guild_removed_command_is_deleted_only_in_that_guild(session: Session) -> None:
    command_id = _add_record(session, "old")
    _add_guild_row(session, command_id, 1, "() -> None", "10")
    _add_guild_row(session, command_id, 2, "() -> None", "11")

    plan = diff_guild_commands(session, 1, [])
    assert plan.to_create == []
    assert plan.to_edit == []
    assert plan.to_delete == ["10"]
