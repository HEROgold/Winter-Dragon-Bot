"""Unit tests: Bot's command registry, INTERACTION_CREATE dispatch and startup sync (no real Discord calls)."""

from __future__ import annotations

import asyncio
import types
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import wd_bot.bot as bot_module
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select
from wd_bot.auto_sync import CommandRecord, GlobalSyncedCommand
from wd_bot.bot import Bot
from wd_bot.cogs import Cog
from wd_bot.commands import Command
from wd_discord.gateway import EventName
from wd_discord.gateway.events import Interaction, InteractionData, InteractionType
from wd_discord.resources.user import User


if TYPE_CHECKING:
    import pytest


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite so the primary key autoincrements."""
    return "INTEGER"


CALLS: list[Interaction] = []


class _PingCog(Cog, auto_load=False):
    @Cog.command(name="ping", description="d")
    async def ping(self, interaction: Interaction) -> None:
        CALLS.append(interaction)


class _SubPingCog(_PingCog, auto_load=False):
    """Inherits the command from a parent class."""


class _AutoPingCog(Cog):
    """Auto-loading cog (the default), as real extension cogs are."""

    @Cog.command(name="auto-ping", description="d")
    async def auto_ping(self, interaction: Interaction) -> None:
        CALLS.append(interaction)


def _make_bot() -> Bot:
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    return bot


def _make_interaction(name: str) -> Interaction:
    return Interaction(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND,
        token="tok",  # noqa: S106
        version=1,
        user=User.model_validate({"id": "3", "username": "asker", "discriminator": "0"}),
        data=InteractionData(id="10", name=name, type=1),
    )


async def test_add_cog_registers_commands() -> None:
    bot = _make_bot()
    cog = _PingCog(bot=bot)
    await bot.add_cog(cog)
    assert "ping" in bot._commands


async def test_add_cog_registers_inherited_commands() -> None:
    bot = _make_bot()
    cog = _SubPingCog(bot=bot)
    await bot.add_cog(cog)
    assert bot._commands["ping"][0] is cog


async def test_dispatch_interaction_invokes_matching_command() -> None:
    CALLS.clear()
    bot = _make_bot()
    await bot.add_cog(_PingCog(bot=bot))
    interaction = _make_interaction("ping")
    await bot._dispatch_interaction(interaction)
    assert [interaction] == CALLS


async def test_dispatch_interaction_is_registered_as_listener() -> None:
    bot = _make_bot()
    assert bot._dispatch_interaction in bot._listeners[EventName.INTERACTION_CREATE.value]


async def test_dispatch_unknown_command_is_ignored() -> None:
    CALLS.clear()
    bot = _make_bot()
    await bot._dispatch_interaction(_make_interaction("nope"))
    assert CALLS == []


async def test_init_cogs_registers_commands_before_any_other_await() -> None:
    bot = _make_bot()
    module = types.ModuleType("fake_ext")
    module._AutoPingCog = _AutoPingCog  # noqa: SLF001
    module.Cog = Cog
    # _init_cogs must not rely on the scheduled auto_load task: the registry is filled on return.
    await bot._init_cogs(module)
    assert "auto-ping" in bot._commands


def _make_engine() -> object:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return engine


def _fake_client() -> MagicMock:
    client = MagicMock()
    registered = MagicMock()
    registered.id = 555
    client.create_global_command = AsyncMock(return_value=registered)
    client.edit_global_command = AsyncMock(return_value=registered)
    client.delete_global_command = AsyncMock(return_value=None)
    return client


async def test_sync_commands_creates_once_then_is_a_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _make_engine()
    monkeypatch.setattr(bot_module, "engine", engine)
    bot = _make_bot()
    await bot.add_cog(_PingCog(bot=bot))
    client = _fake_client()

    await bot.sync_commands(client)

    client.create_global_command.assert_awaited_once()
    assert client.create_global_command.await_args.args[0] == "ping"
    with Session(engine) as session:
        rows = session.exec(select(GlobalSyncedCommand)).all()
        assert [row.discord_command_id for row in rows] == ["555"]

    await bot.sync_commands(client)

    client.create_global_command.assert_awaited_once()
    client.edit_global_command.assert_not_awaited()
    client.delete_global_command.assert_not_awaited()


async def test_sync_commands_deletes_removed_command(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _make_engine()
    monkeypatch.setattr(bot_module, "engine", engine)
    with Session(engine) as session:
        record = CommandRecord(name="old")
        session.add(record)
        session.commit()
        session.refresh(record)
        session.add(GlobalSyncedCommand(command_id=record.id, signature="() -> None", discord_command_id="77"))
        session.commit()
    bot = _make_bot()
    client = _fake_client()

    await bot.sync_commands(client)

    client.delete_global_command.assert_awaited_once_with("77")
    with Session(engine) as session:
        assert session.exec(select(GlobalSyncedCommand)).all() == []


async def test_sync_commands_edits_changed_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _make_engine()
    monkeypatch.setattr(bot_module, "engine", engine)
    with Session(engine) as session:
        record = CommandRecord(name="ping")
        session.add(record)
        session.commit()
        session.refresh(record)
        session.add(GlobalSyncedCommand(command_id=record.id, signature="stale", discord_command_id="88"))
        session.commit()
    bot = _make_bot()
    await bot.add_cog(_PingCog(bot=bot))
    client = _fake_client()

    await bot.sync_commands(client)

    client.edit_global_command.assert_awaited_once()
    assert client.edit_global_command.await_args.args[0] == "88"
    with Session(engine) as session:
        row = session.exec(select(GlobalSyncedCommand)).one()
        assert row.signature == Command.signature(bot._commands["ping"][1])
