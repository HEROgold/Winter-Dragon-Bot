"""Diff-based sync tracking for Discord application commands.

Tracks which commands are currently registered with Discord (globally, and - built but unused in
v1, see the design doc's "Deferred: guild scoping" - per guild) so the bot only issues create/edit/
delete REST calls for commands whose definition actually changed, never a full re-push.
"""

from __future__ import annotations

lazy from dataclasses import dataclass, field
lazy from typing import TYPE_CHECKING, Protocol

lazy from sqlmodel import Field, Session, UniqueConstraint, select
lazy from wd_db.extension.model import SQLModel


if TYPE_CHECKING:
    lazy from collections.abc import Sequence


class CommandLike(Protocol):
    """Anything with a stable name and a signature - satisfied structurally by wd_bot.commands.Command."""

    name: str

    def signature(self) -> str:
        """Return the command's signature string."""
        ...


class CommandRecord(SQLModel, table=True):
    """The identity of a known command, independent of which scope(s) it's synced to."""

    name: str = Field(unique=True)


class GlobalSyncedCommand(SQLModel, table=True):
    """Tracks one command's global sync state: its last-synced signature and Discord's assigned ID.

    ``discord_command_id`` is ``str``, not ``Snowflake`` - no SQLModel table in this codebase
    stores a ``Snowflake`` column today (it has a pydantic core schema but no SQLAlchemy type
    adapter). TODO: switch to a real ``Snowflake`` column once one exists.
    """

    command_id: int = Field(foreign_key="commandrecord.id", unique=True)
    signature: str
    discord_command_id: str


class GuildSyncedCommand(SQLModel, table=True):
    """Per-guild counterpart to :class:`GlobalSyncedCommand`.

    Built now per the design doc (cheap and symmetrical to write alongside the global table), but
    unreachable in v1 - ``Cog.command()`` has no ``guild_ids`` parameter yet.
    """

    command_id: int = Field(foreign_key="commandrecord.id")
    guild_id: int
    signature: str
    discord_command_id: str

    __table_args__ = (UniqueConstraint("command_id", "guild_id"),)


@dataclass
class SyncPlan:
    """The set of REST calls needed to reconcile registered commands with Discord's actual state."""

    to_create: list[CommandLike] = field(default_factory=list[CommandLike])
    to_edit: list[tuple[CommandLike, str]] = field(default_factory=list[tuple[CommandLike, str]])
    to_delete: list[str] = field(default_factory=list[str])


def _get_or_create_record(session: Session, name: str) -> CommandRecord:  # pyright: ignore[reportUnusedFunction]
    """Return the :class:`CommandRecord` named ``name``, creating and committing it if missing."""
    record = session.exec(select(CommandRecord).where(CommandRecord.name == name)).first()
    if record is None:
        record = CommandRecord(name=name)
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


def _build_plan(
    commands: Sequence[CommandLike],
    records_by_name: dict[str, CommandRecord],
    synced_by_command_id: dict[int, GlobalSyncedCommand] | dict[int, GuildSyncedCommand],
) -> SyncPlan:
    """Compute the :class:`SyncPlan` for ``commands`` given the known records and their synced rows."""
    plan = SyncPlan()

    live_names: set[str] = set()
    for command in commands:
        live_names.add(command.name)
        record = records_by_name.get(command.name)
        row = synced_by_command_id.get(record.id) if record and record.id is not None else None
        if row is None:
            plan.to_create.append(command)
        elif row.signature != command.signature():
            plan.to_edit.append((command, row.discord_command_id))

    for record in records_by_name.values():
        if record.name in live_names or record.id is None:
            continue
        row = synced_by_command_id.get(record.id)
        if row is not None:
            plan.to_delete.append(row.discord_command_id)

    return plan


def diff_global_commands(session: Session, commands: Sequence[CommandLike]) -> SyncPlan:
    """Compare ``commands`` against :class:`GlobalSyncedCommand` rows and plan the minimal sync."""
    records_by_name = {record.name: record for record in session.exec(select(CommandRecord)).all()}
    synced_by_command_id = {row.command_id: row for row in session.exec(select(GlobalSyncedCommand)).all()}
    return _build_plan(commands, records_by_name, synced_by_command_id)


def diff_guild_commands(session: Session, guild_id: int, commands: Sequence[CommandLike]) -> SyncPlan:
    """Guild-scoped counterpart to :func:`diff_global_commands` (see class docstrings - unused in v1)."""
    records_by_name = {record.name: record for record in session.exec(select(CommandRecord)).all()}
    rows = session.exec(select(GuildSyncedCommand).where(GuildSyncedCommand.guild_id == guild_id)).all()
    synced_by_command_id = {row.command_id: row for row in rows}
    return _build_plan(commands, records_by_name, synced_by_command_id)
