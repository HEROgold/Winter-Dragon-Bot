"""Unit tests: DefaultCommandSyncer pushes only needed changes (in-memory sqlite, recording client)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, override

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select
from wd_bot.auto_sync import CommandRecord, DefaultCommandSyncer, GlobalSyncedCommand
from wd_bot.commands import Command
from wd_discord.errors.api import ApiResponseError
from wd_discord.permissions import Permissions
from wd_discord.testing import RecordingClient


if TYPE_CHECKING:
    import pytest
    from httpxyz import Response
    from sqlalchemy import Engine
    from wd_discord import CommandInteraction


COMMANDS = "/applications/2/commands"
REGISTERED = {"id": "555", "application_id": "2", "name": "ping", "description": "d", "version": "1"}
UNKNOWN_COMMAND = ApiResponseError(code=10063, message="Unknown application command")


async def _ping(self: object, interaction: CommandInteraction) -> None:
    """Handle a no-option command."""


def _command() -> Command:
    return Command(_ping, name="ping", description="d")


def _client() -> RecordingClient:
    """Return a client on which every create and edit of command 88 succeeds as command 555."""
    client = RecordingClient()
    client.reply("POST", COMMANDS, REGISTERED)
    client.reply("PATCH", f"{COMMANDS}/88", REGISTERED)
    return client


def _calls(client: RecordingClient, method: str, path: str = COMMANDS) -> list[Any]:
    """Return the JSON bodies of ``client``'s ``method`` requests to ``path``."""
    return [sent.json for sent in client.requests_to(method, path)]


def _synced_ids(engine: Engine) -> list[str]:
    with Session(engine) as session:
        return [row.discord_command_id for row in session.exec(select(GlobalSyncedCommand)).all()]


def _seed(engine: Engine, name: str, signature: str, discord_id: str) -> None:
    with Session(engine) as session:
        record = CommandRecord(name=name)
        session.add(record)
        session.commit()
        session.refresh(record)
        session.add(GlobalSyncedCommand(command_id=record.id, signature=signature, discord_command_id=discord_id))
        session.commit()


async def test_creates_once_then_is_a_noop(engine: Engine) -> None:
    syncer = DefaultCommandSyncer(engine=engine)
    client = _client()
    commands = [_command()]

    await syncer.sync(client, commands)

    assert [body["name"] for body in _calls(client, "POST")] == ["ping"]
    assert _synced_ids(engine) == ["555"]

    await syncer.sync(client, commands)

    assert len(client.sent) == 1


async def test_deletes_removed_command(engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _client()

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    assert len(client.requests_to("DELETE", f"{COMMANDS}/77")) == 1
    assert _synced_ids(engine) == ["555"]


async def test_edits_changed_signature(engine: Engine) -> None:
    command = _command()
    _seed(engine, "ping", "stale", "88")
    client = _client()

    await DefaultCommandSyncer(engine=engine).sync(client, [command])

    assert len(client.requests_to("PATCH", f"{COMMANDS}/88")) == 1
    with Session(engine) as session:
        assert session.exec(select(GlobalSyncedCommand)).one().signature == command.signature()


async def test_allow_deletes_false_skips_deletes_and_keeps_rows(capsys: pytest.CaptureFixture[str], engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _client()

    await DefaultCommandSyncer(engine=engine).sync(client, [], allow_deletes=False)

    assert client.requests_to("DELETE", f"{COMMANDS}/77") == []
    assert len(_synced_ids(engine)) == 1
    assert "77" in capsys.readouterr().err


async def test_failed_create_writes_no_row_and_is_retried(engine: Engine) -> None:
    syncer = DefaultCommandSyncer(engine=engine)
    client = _client()
    client.fail("POST", COMMANDS, ApiResponseError(code=500, message="boom"))
    commands = [_command()]

    await syncer.sync(client, commands)
    assert _synced_ids(engine) == []

    await syncer.sync(client, commands)
    assert len(_calls(client, "POST")) == len(commands) * 2


async def test_failed_delete_keeps_row(engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _client()
    client.fail("DELETE", f"{COMMANDS}/77", ApiResponseError(code=500, message="boom"))

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    assert len(client.requests_to("DELETE", f"{COMMANDS}/77")) == 1
    assert len(_synced_ids(engine)) == 2


class _VanishingRowClient(RecordingClient):
    """Deletes every synced row while an edit is in flight, as a concurrent cleanup would."""

    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self.engine = engine

    @override
    async def request(self, method: str, path: str, **kwargs: Any) -> Response | ApiResponseError:  # pyright: ignore[reportIncompatibleMethodOverride]
        if method == "PATCH":
            with Session(self.engine) as session:
                for row in session.exec(select(GlobalSyncedCommand)).all():
                    session.delete(row)
                session.commit()
        return await super().request(method, path, **kwargs)


async def test_edit_with_missing_row_warns_and_continues(capsys: pytest.CaptureFixture[str], engine: Engine) -> None:
    _seed(engine, "ping", "stale", "88")
    client = _VanishingRowClient(engine)
    client.reply("PATCH", f"{COMMANDS}/88", REGISTERED)

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    assert len(client.requests_to("PATCH", f"{COMMANDS}/88")) == 1
    assert "No synced row" in capsys.readouterr().err


async def test_passes_default_member_permissions_to_create_and_edit(engine: Engine) -> None:
    syncer = DefaultCommandSyncer(engine=engine)
    client = _client()
    client.reply("PATCH", f"{COMMANDS}/555", REGISTERED)
    gated = Command(_ping, name="ping", description="d", default_member_permissions=Permissions.MANAGE_GUILD)

    await syncer.sync(client, [gated])
    assert _calls(client, "POST")[0]["default_member_permissions"] == str(int(Permissions.MANAGE_GUILD))

    changed = Command(_ping, name="ping", description="d2", default_member_permissions=Permissions.ADMINISTRATOR)
    await syncer.sync(client, [changed])
    assert _calls(client, "PATCH", f"{COMMANDS}/555")[0]["default_member_permissions"] == str(int(Permissions.ADMINISTRATOR))


async def test_sync_creates_its_own_tables_on_a_fresh_engine() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    client = _client()

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    assert len(_calls(client, "POST")) == 1
    assert _synced_ids(engine) == ["555"]


async def test_edit_of_unknown_command_recreates_it(engine: Engine) -> None:
    _seed(engine, "ping", "stale", "88")
    client = _client()
    client.fail("PATCH", f"{COMMANDS}/88", UNKNOWN_COMMAND)

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    assert len(client.requests_to("PATCH", f"{COMMANDS}/88")) == 1
    assert len(_calls(client, "POST")) == 1
    with Session(engine) as session:
        row = session.exec(select(GlobalSyncedCommand)).one()
        assert row.discord_command_id == "555"
        assert row.signature == _command().signature()


async def test_edit_with_bare_404_recreates_it(engine: Engine) -> None:
    _seed(engine, "ping", "stale", "88")
    client = _client()
    client.fail("PATCH", f"{COMMANDS}/88", ApiResponseError(code=404, message="Not Found"))

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    assert _synced_ids(engine) == ["555"]


async def test_delete_of_unknown_command_counts_as_success(engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _client()
    client.fail("DELETE", f"{COMMANDS}/77", UNKNOWN_COMMAND)

    await DefaultCommandSyncer(engine=engine).sync(client, [_command()])

    assert len(client.requests_to("DELETE", f"{COMMANDS}/77")) == 1
    assert _synced_ids(engine) == ["555"]


class _SlowClient(RecordingClient):
    """Takes a moment to answer, so two syncs overlap."""

    @override
    async def request(self, method: str, path: str, **kwargs: Any) -> Response | ApiResponseError:  # pyright: ignore[reportIncompatibleMethodOverride]
        await asyncio.sleep(0.01)
        return await super().request(method, path, **kwargs)


async def test_concurrent_syncs_do_not_double_create(engine: Engine) -> None:
    syncer = DefaultCommandSyncer(engine=engine)
    client = _SlowClient()
    client.reply("POST", COMMANDS, REGISTERED)
    commands = [_command()]

    await asyncio.gather(syncer.sync(client, commands), syncer.sync(client, commands))

    assert len(_calls(client, "POST")) == 1
    assert len(_synced_ids(engine)) == 1


async def test_empty_command_list_skips_mass_delete(capsys: pytest.CaptureFixture[str], engine: Engine) -> None:
    _seed(engine, "old", "() -> None", "77")
    client = _client()

    await DefaultCommandSyncer(engine=engine).sync(client, [])

    assert client.requests_to("DELETE", f"{COMMANDS}/77") == []
    assert len(_synced_ids(engine)) == 1
    assert "refusing to mass-delete" in capsys.readouterr().err
