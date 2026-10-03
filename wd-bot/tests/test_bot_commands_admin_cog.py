"""Unit tests: the admin bot-commands cog's status formatting and handlers (no network)."""

from __future__ import annotations

lazy from types import SimpleNamespace
lazy from typing import TYPE_CHECKING
lazy from unittest.mock import AsyncMock, MagicMock

lazy from sqlalchemy import BigInteger
lazy from sqlalchemy.ext.compiler import compiles
lazy from sqlalchemy.pool import StaticPool
lazy from sqlmodel import Session, SQLModel, create_engine
lazy from wd_bot.auto_sync import CommandRecord, GlobalSyncedCommand
lazy from wd_bot.commands import Command, CommandGroup
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.permissions import Permissions

lazy import winter_dragon.cogs.bot_commands as module
lazy from winter_dragon.cogs.bot_commands import BotCommands, describe_sync_status


if TYPE_CHECKING:
    lazy from sqlalchemy import Engine
    lazy from wd_discord.gateway.events import Interaction


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite so the primary key autoincrements."""
    return "INTEGER"


async def _noop(self: object, interaction: Interaction) -> None:
    """Handle a no-option command."""


def _engine() -> Engine:
    """Build an in-memory sqlite engine with all tables."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return engine


def _seed_synced(engine: Engine, name: str, signature: str) -> None:
    """Record ``name`` as synced with ``signature``."""
    with Session(engine) as session:
        record = CommandRecord(name=name)
        session.add(record)
        session.commit()
        session.refresh(record)
        assert record.id is not None
        session.add(GlobalSyncedCommand(command_id=record.id, signature=signature, discord_command_id="1"))
        session.commit()


def test_describe_sync_status_reports_synced_and_pending() -> None:
    engine = _engine()
    _seed_synced(engine, "percentage", "sig")
    with Session(engine) as session:
        lines = list(describe_sync_status(session, [("percentage", "sig"), ("other", "sig2")]))
    assert "percentage: synced" in lines
    assert "other: pending" in lines


def test_describe_sync_status_reports_stale_signature_as_pending() -> None:
    engine = _engine()
    _seed_synced(engine, "percentage", "old")
    with Session(engine) as session:
        assert list(describe_sync_status(session, [("percentage", "new")])) == ["percentage: pending"]


def test_group_is_gated_to_manage_guild() -> None:
    (group,) = BotCommands.app_commands()
    assert isinstance(group, CommandGroup)
    assert group.name == "bot-commands"
    assert group.default_member_permissions == Permissions.MANAGE_GUILD
    assert sorted(group.subcommands) == ["list", "resync"]
    assert all(command.default_member_permissions is None for command in group.subcommands.values())


async def test_list_commands_replies_with_status_embed(monkeypatch: object) -> None:
    engine = _engine()
    command = Command(_noop, name="ping", description="d")
    _seed_synced(engine, "ping", command.signature())
    monkeypatch.setattr(module, "engine", engine)  # pyright: ignore[reportAttributeAccessIssue]
    respond = AsyncMock()
    cog = BotCommands.__new__(BotCommands)
    cog.bot = SimpleNamespace(commands=iter([command]), client=SimpleNamespace(create_interaction_response=respond))  # pyright: ignore[reportAttributeAccessIssue]
    interaction = MagicMock()

    await BotCommands.list_commands.invoke(cog, interaction)

    respond.assert_awaited_once()
    embed = respond.await_args.kwargs["embeds"][0]
    assert embed.description == "ping: synced"


async def test_resync_responds_before_syncing() -> None:
    order: list[str] = []
    client = SimpleNamespace(create_interaction_response=AsyncMock(side_effect=lambda *_a, **_k: order.append("respond")))
    sync = AsyncMock(side_effect=lambda *_a, **_k: order.append("sync"))
    cog = BotCommands.__new__(BotCommands)
    cog.bot = SimpleNamespace(commands=iter(()), client=client, sync_commands=sync)  # pyright: ignore[reportAttributeAccessIssue]
    interaction = MagicMock()

    await BotCommands.resync.invoke(cog, interaction)

    assert order == ["respond", "sync"]
    sync.assert_awaited_once_with(client)
    client.create_interaction_response.assert_awaited_once_with(interaction, content="Resyncing commands…")


def test_group_is_guild_only() -> None:
    """Discord doesn't enforce default_member_permissions in DMs, so the admin group must not show up there."""
    (group,) = BotCommands.app_commands()
    assert group.params().contexts == [InteractionContextType.GUILD]


def test_resync_description() -> None:
    assert BotCommands.resync.description == "Push pending command changes to Discord"
