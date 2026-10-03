"""Unit tests: DefaultCommandSyncer pushes only needed changes (in-memory sqlite, fake client)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select
from wd_bot.auto_sync import CommandRecord, DefaultCommandSyncer, GlobalSyncedCommand
from wd_bot.commands import Command
from wd_discord.errors.api import ApiResponseError
from wd_discord.permissions import Permissions


if TYPE_CHECKING:
    import pytest
    from sqlalchemy import Engine
    from wd_discord.gateway.events import Interaction



async def _ping(self: object, interaction: Interaction) -> None:
    """Handle a no-option command."""


def _command() -> Command:
    return Command(_ping, name="ping", description="d")




def _fake_client() -> MagicMock:
    client = MagicMock()
    registered = MagicMock()
    registered.id = 555
    client.create_global_command = AsyncMock(return_value=registered)
    client.edit_global_command = AsyncMock(return_value=registered)
    client.delete_global_command = AsyncMock(return_value=None)
    return client


async def test_creates_once_then_is_a_noop(engine: Engine) -> None:
    syncer = DefaultCommandSyncer(engine=engine)
    client = _fake_client()
    commands = [_command()]

    await syncer.sync(client, commands)

    client.create_global_command.assert_awaited_once()
    assert client.create_global_command.await_args.args[0].name == "ping"
    with Session(engine) as session:
        rows = session.exec(select(GlobalSyncedCommand)).all()
        assert [row.discord_command_id for row in rows] == ["555"]

    await syncer.sync(client, commands)

    client.create_global_command.assert_awaited_once()
    client.edit_global_command.assert_not_awaited()
    client.delete_global_command.assert_not_awaited()


async def test_deletes_removed_command(engine: Engine) -> None:
    with Session(engine) as session:
        record = CommandRecord(name="old")
        session.add(record)
        session.commit()
        session.refresh(record)
        session.add(GlobalSyncedCommand(command_id=record.id, signature="() -> None", discord_command_id="77"))
        session.commit()
    client = _fake_client()

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    client.delete_global_command.assert_awaited_once_with("77")
    with Session(engine) as session:
        assert [row.discord_command_id for row in session.exec(select(GlobalSyncedCommand)).all()] == ["555"]


async def test_edits_changed_signature(engine: Engine) -> None:
    command = _command()
    with Session(engine) as session:
        record = CommandRecord(name="ping")
        session.add(record)
        session.commit()
        session.refresh(record)
        session.add(GlobalSyncedCommand(command_id=record.id, signature="stale", discord_command_id="88"))
        session.commit()
    client = _fake_client()

    await DefaultCommandSyncer(engine=engine).sync(client, [command])

    client.edit_global_command.assert_awaited_once()
    assert client.edit_global_command.await_args.args[0] == "88"
    with Session(engine) as session:
        assert session.exec(select(GlobalSyncedCommand)).one().signature == command.signature()


def _seed(engine: Engine, name: str, signature: str, discord_id: str) -> None:
    with Session(engine) as session:
        record = CommandRecord(name=name)
        session.add(record)
        session.commit()
        session.refresh(record)
        session.add(GlobalSyncedCommand(command_id=record.id, signature=signature, discord_command_id=discord_id))
        session.commit()


async def test_allow_deletes_false_skips_deletes_and_keeps_rows(capsys: pytest.CaptureFixture[str], engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _fake_client()

    await DefaultCommandSyncer(engine=engine).sync(client, [], allow_deletes=False)

    client.delete_global_command.assert_not_awaited()
    with Session(engine) as session:
        assert len(session.exec(select(GlobalSyncedCommand)).all()) == 1
    assert "77" in capsys.readouterr().err


async def test_failed_create_writes_no_row_and_is_retried(engine: Engine) -> None:
    syncer = DefaultCommandSyncer(engine=engine)
    client = _fake_client()
    client.create_global_command = AsyncMock(return_value=ApiResponseError(code=500, message="boom"))
    commands = [_command()]

    await syncer.sync(client, commands)
    with Session(engine) as session:
        assert session.exec(select(GlobalSyncedCommand)).all() == []

    await syncer.sync(client, commands)
    assert client.create_global_command.await_count == len(commands) * 2


async def test_failed_delete_keeps_row(engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _fake_client()
    client.delete_global_command = AsyncMock(return_value=ApiResponseError(code=500, message="boom"))

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    client.delete_global_command.assert_awaited_once_with("77")
    with Session(engine) as session:
        assert len(session.exec(select(GlobalSyncedCommand)).all()) == 2


async def test_edit_with_missing_row_warns_and_continues(capsys: pytest.CaptureFixture[str], engine: Engine) -> None:
    _seed(engine, "ping", "stale", "88")
    client = _fake_client()

    async def vanish(*_args: object, **_kwargs: object) -> MagicMock:
        with Session(engine) as session:
            for row in session.exec(select(GlobalSyncedCommand)).all():
                session.delete(row)
            session.commit()
        return client.create_global_command.return_value

    client.edit_global_command = AsyncMock(side_effect=vanish)
    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    client.edit_global_command.assert_awaited_once()
    assert "No synced row" in capsys.readouterr().err


async def test_passes_default_member_permissions_to_create_and_edit(engine: Engine) -> None:
    syncer = DefaultCommandSyncer(engine=engine)
    client = _fake_client()
    gated = Command(_ping, name="ping", description="d", default_member_permissions=Permissions.MANAGE_GUILD)

    await syncer.sync(client, [gated])
    assert client.create_global_command.await_args.args[0].default_member_permissions == Permissions.MANAGE_GUILD

    changed = Command(_ping, name="ping", description="d2", default_member_permissions=Permissions.ADMINISTRATOR)
    await syncer.sync(client, [changed])
    assert client.edit_global_command.await_args.args[1].default_member_permissions == Permissions.ADMINISTRATOR


async def test_sync_creates_its_own_tables_on_a_fresh_engine() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    client = _fake_client()

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    client.create_global_command.assert_awaited_once()
    with Session(engine) as session:
        assert [row.discord_command_id for row in session.exec(select(GlobalSyncedCommand)).all()] == ["555"]


async def test_edit_of_unknown_command_recreates_it(engine: Engine) -> None:
    _seed(engine, "ping", "stale", "88")
    client = _fake_client()
    client.edit_global_command = AsyncMock(
        return_value=ApiResponseError(code=10063, message="Unknown application command"),
    )

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    client.edit_global_command.assert_awaited_once()
    client.create_global_command.assert_awaited_once()
    with Session(engine) as session:
        row = session.exec(select(GlobalSyncedCommand)).one()
        assert row.discord_command_id == "555"
        assert row.signature == _command().signature()


async def test_edit_with_bare_404_recreates_it(engine: Engine) -> None:
    _seed(engine, "ping", "stale", "88")
    client = _fake_client()
    client.edit_global_command = AsyncMock(return_value=ApiResponseError(code=404, message="Not Found"))

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    with Session(engine) as session:
        assert [row.discord_command_id for row in session.exec(select(GlobalSyncedCommand)).all()] == ["555"]


async def test_delete_of_unknown_command_counts_as_success(engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _fake_client()
    client.delete_global_command = AsyncMock(
        return_value=ApiResponseError(code=10063, message="Unknown application command"),
    )

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    client.delete_global_command.assert_awaited_once_with("77")
    with Session(engine) as session:
        assert [row.discord_command_id for row in session.exec(select(GlobalSyncedCommand)).all()] == ["555"]


async def test_concurrent_syncs_do_not_double_create(engine: Engine) -> None:
    syncer = DefaultCommandSyncer(engine=engine)
    client = _fake_client()
    registered = client.create_global_command.return_value

    async def slow_create(*_args: object, **_kwargs: object) -> MagicMock:
        await asyncio.sleep(0.01)
        return registered

    client.create_global_command = AsyncMock(side_effect=slow_create)
    commands = [_command()]

    await asyncio.gather(syncer.sync(client, commands), syncer.sync(client, commands))

    client.create_global_command.assert_awaited_once()
    with Session(engine) as session:
        assert len(session.exec(select(GlobalSyncedCommand)).all()) == 1


async def test_empty_command_list_skips_mass_delete(capsys: pytest.CaptureFixture[str], engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _fake_client()

    await DefaultCommandSyncer(engine=engine).sync(client, [])

    client.delete_global_command.assert_not_awaited()
    with Session(engine) as session:
        assert len(session.exec(select(GlobalSyncedCommand)).all()) == 1
    assert "refusing to mass-delete" in capsys.readouterr().err
