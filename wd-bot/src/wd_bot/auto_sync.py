"""Diff-based sync tracking for Discord application commands.

Tracks which commands are currently registered with Discord (globally, and - built but unused in
v1, see the design doc's "Deferred: guild scoping" - per guild) so the bot only issues create/edit/
delete REST calls for commands whose definition actually changed, never a full re-push.
"""

from __future__ import annotations

lazy import asyncio
lazy from abc import ABC, abstractmethod
lazy from dataclasses import dataclass, field
lazy from typing import TYPE_CHECKING, Protocol, override

lazy from herogold.log import LoggerMixin
lazy from sqlmodel import Field, Session, UniqueConstraint, select
lazy from wd_db.constants import engine as default_engine
lazy from wd_db.extension.model import SQLModel
lazy from wd_discord.client import is_network_error
lazy from wd_discord.errors.api import ApiResponseError


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Iterable, Sequence

    lazy from sqlalchemy import ColumnElement, Engine
    lazy from wd_discord import Client

    lazy from wd_bot.commands import AppCommand


UNKNOWN_COMMAND_CODES = frozenset({404, 10063})
"""Error codes meaning Discord has no such command: HTTP 404 and JSON code 10063 ("Unknown application command")."""


class CommandLike(Protocol):
    """Anything with a stable name and a signature - satisfied structurally by wd_bot.commands.Command."""

    name: str

    def signature(self) -> str:
        """Return the command's signature string."""
        ...


class SyncedRow(Protocol):
    """One command's sync state in some scope - satisfied by :class:`GlobalSyncedCommand` and :class:`GuildSyncedCommand`."""

    command_id: int
    signature: str
    discord_command_id: str


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


def _get_or_create_record(session: Session, name: str) -> CommandRecord:
    """Return the :class:`CommandRecord` named ``name``, creating and committing it if missing."""
    record = session.exec(select(CommandRecord).where(CommandRecord.name == name)).first()
    if record is None:
        record = CommandRecord(name=name)
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


def _locked_row(session: Session, discord_command_id: str) -> GlobalSyncedCommand | None:
    """Return the :class:`GlobalSyncedCommand` for ``discord_command_id``, locked for update, if any."""
    return session.exec(
        select(GlobalSyncedCommand).where(GlobalSyncedCommand.discord_command_id == discord_command_id).with_for_update(),
    ).first()


def _is_unknown_command(result: object) -> bool:
    """Whether ``result`` is Discord's "Unknown application command" error (or a bare 404).

    ``ApiResponseError.code`` carries Discord's JSON error code (10063) when the body parsed, and
    the HTTP status (404) when it didn't.
    """
    return isinstance(result, ApiResponseError) and result.code in UNKNOWN_COMMAND_CODES


class SyncedCommands[Row: SyncedRow]:
    """The known command records and their synced rows in one scope (global, or one guild)."""

    def __init__(self, records: Iterable[CommandRecord], rows: Iterable[Row]) -> None:
        """Index ``records`` by name and ``rows`` by the record they belong to."""
        self._records_by_name = {record.name: record for record in records}
        self._rows_by_command_id = {row.command_id: row for row in rows}

    @classmethod
    def load(cls, session: Session, row_model: type[Row], *where: ColumnElement[bool] | bool) -> SyncedCommands[Row]:
        """Read every record, and the ``row_model`` rows matching ``where``, from ``session``."""
        records = session.exec(select(CommandRecord)).all()
        rows = session.exec(select(row_model).where(*where)).all()
        return cls(records, rows)

    def row_for(self, name: str) -> Row | None:
        """Return the synced row for the command named ``name``, if it was synced in this scope."""
        record = self._records_by_name.get(name)
        if record is None or record.id is None:
            return None
        return self._rows_by_command_id.get(record.id)

    def is_synced(self, name: str, signature: str) -> bool:
        """Whether the command named ``name`` was last synced with exactly ``signature``."""
        row = self.row_for(name)
        return row is not None and row.signature == signature

    def plan(self, commands: Sequence[CommandLike]) -> SyncPlan:
        """Compute the :class:`SyncPlan` that brings this scope in line with ``commands``."""
        plan = SyncPlan(to_delete=list(self._plan_deletes(commands)))
        self._plan_upserts(plan, commands)
        return plan

    def _plan_upserts(self, plan: SyncPlan, commands: Sequence[CommandLike]) -> None:
        """Add each command that was never synced to ``to_create``, and each changed one to ``to_edit``."""
        for command in commands:
            row = self.row_for(command.name)
            if row is None:
                plan.to_create.append(command)
            elif row.signature != command.signature():
                plan.to_edit.append((command, row.discord_command_id))

    def _plan_deletes(self, commands: Sequence[CommandLike]) -> Generator[str]:
        """Yield the Discord IDs of synced commands that are no longer in ``commands``."""
        live_names = {command.name for command in commands}
        for name in self._records_by_name.keys() - live_names:
            row = self.row_for(name)
            if row is not None:
                yield row.discord_command_id


def command_mention(session: Session, name: str, subcommand: str | None = None) -> str:
    """Return a clickable ``</name subcommand:id>`` mention of a globally synced command.

    Falls back to a plain ``/name subcommand`` while the command hasn't been synced yet (no Discord ID known).
    """
    full_name = name if subcommand is None else f"{name} {subcommand}"
    row = SyncedCommands.load(session, GlobalSyncedCommand).row_for(name)
    return f"`/{full_name}`" if row is None else f"</{full_name}:{row.discord_command_id}>"


def diff_global_commands(session: Session, commands: Sequence[CommandLike]) -> SyncPlan:
    """Compare ``commands`` against :class:`GlobalSyncedCommand` rows and plan the minimal sync."""
    return SyncedCommands.load(session, GlobalSyncedCommand).plan(commands)


def diff_guild_commands(session: Session, guild_id: int, commands: Sequence[CommandLike]) -> SyncPlan:
    """Guild-scoped counterpart to :func:`diff_global_commands` (see class docstrings - unused in v1)."""
    return SyncedCommands.load(session, GuildSyncedCommand, GuildSyncedCommand.guild_id == guild_id).plan(commands)


class CommandSyncer(ABC):
    """Strategy for reconciling the bot's registered commands with Discord."""

    @abstractmethod
    async def sync(self, client: Client, commands: Sequence[AppCommand], *, allow_deletes: bool = True) -> None:
        """Push ``commands`` to Discord through ``client``, doing only the work needed.

        With ``allow_deletes`` False, commands missing from ``commands`` are left on Discord.
        """


class DefaultCommandSyncer(CommandSyncer, LoggerMixin):
    """Diff-based :class:`CommandSyncer` tracking last-synced state in the database (global scope only)."""

    def __init__(self, engine: Engine | None = None) -> None:
        """Use ``engine`` for sync state; defaults to ``wd_db.constants.engine``, resolved at sync time."""
        self._engine = engine
        self._tables_ready = False
        self._lock = asyncio.Lock()

    def _ensure_tables(self, engine: Engine) -> None:
        """Create the sync-tracking tables on ``engine`` if missing; runs once per syncer (idempotent)."""
        if self._tables_ready:
            return
        models = (CommandRecord, GlobalSyncedCommand, GuildSyncedCommand)
        # SQLModel's default ``__tablename__`` is the lowercased class name; looking tables up through
        # the metadata keeps them typed as ``Table`` (``Model.__table__`` is untyped).
        tables = [SQLModel.metadata.tables[model.__name__.lower()] for model in models]
        SQLModel.metadata.create_all(engine, tables=tables)
        self._tables_ready = True

    @override
    async def sync(self, client: Client, commands: Sequence[AppCommand], *, allow_deletes: bool = True) -> None:
        """Diff ``commands`` against the last-synced state and push only the changes to Discord.

        With ``allow_deletes`` False, ``plan.to_delete`` is skipped and one warning lists the skipped IDs.
        Deletes are likewise skipped (with a warning) when ``commands`` is empty, guarding against a
        broken load wiping every command from Discord. Concurrent calls are serialized, so two
        overlapping syncs can't both create the same command.
        """
        async with self._lock:
            await self._sync(client, commands, allow_deletes=allow_deletes)

    async def _sync(self, client: Client, commands: Sequence[AppCommand], *, allow_deletes: bool) -> None:
        """Body of :meth:`sync`, run while holding the sync lock."""
        by_name = {command.name: command for command in commands}
        engine = self._engine or default_engine
        self._ensure_tables(engine)
        with Session(engine) as session:
            plan = diff_global_commands(session, list(by_name.values()))
            for planned in plan.to_create:
                await self._create(client, session, by_name[planned.name])
            for planned, discord_command_id in plan.to_edit:
                await self._edit(client, session, by_name[planned.name], discord_command_id)
            if self._deletes_allowed(plan, allow_deletes=allow_deletes, has_commands=bool(by_name)):
                await self._delete(client, session, plan.to_delete)

    def _deletes_allowed(self, plan: SyncPlan, *, allow_deletes: bool, has_commands: bool) -> bool:
        """Whether to run ``plan.to_delete``, warning about any deletes that get skipped."""
        if not plan.to_delete:
            return False
        if not allow_deletes:
            self.logger.warning(t"Skipping deletes of Discord commands {plan.to_delete}")
            return False
        if not has_commands:
            # An empty registry almost always means loading broke, not that every command was removed.
            self.logger.warning(t"No commands registered; refusing to mass-delete Discord commands {plan.to_delete}")
            return False
        return True

    async def _create(self, client: Client, session: Session, command: AppCommand) -> None:
        """Create ``command`` on Discord and store its synced row, unless the create failed."""
        result = await client.create_global_command(command.params())
        if is_network_error(result):
            self.logger.warning(t"Failed to create command '{command.name}': {result}")
            return
        record = _get_or_create_record(session, command.name)
        if record.id is None:
            return
        session.add(
            GlobalSyncedCommand(
                command_id=record.id,
                signature=command.signature(),
                discord_command_id=str(result.id),
            ),
        )
        session.commit()

    async def _edit(self, client: Client, session: Session, command: AppCommand, discord_command_id: str) -> None:
        """Edit ``command`` on Discord and update its synced row's signature.

        If Discord no longer knows the command (deleted out-of-band), the stale row is dropped and
        the command is created afresh in the same sync.
        """
        result = await client.edit_global_command(discord_command_id, command.params())
        if _is_unknown_command(result):
            await self._recreate(client, session, command, discord_command_id)
            return
        if is_network_error(result):
            self.logger.warning(t"Failed to edit command '{command.name}': {result}")
            return
        row = _locked_row(session, discord_command_id)
        if row is None:
            self.logger.warning(t"No synced row for edited command '{command.name}'")
            return
        row.signature = command.signature()
        session.add(row)
        session.commit()

    async def _recreate(self, client: Client, session: Session, command: AppCommand, discord_command_id: str) -> None:
        """Drop the stale row of a command Discord no longer knows, then create the command afresh."""
        self.logger.warning(t"Command '{command.name}' ({discord_command_id}) is gone on Discord; recreating it")
        self._drop_row(session, discord_command_id)
        await self._create(client, session, command)

    async def _delete(self, client: Client, session: Session, discord_command_ids: Sequence[str]) -> None:
        """Delete ``discord_command_ids`` on Discord, dropping each synced row only if its delete succeeded.

        A delete of a command Discord no longer knows counts as success.
        """
        for discord_command_id in discord_command_ids:
            result = await client.delete_global_command(discord_command_id)
            if is_network_error(result) and not _is_unknown_command(result):
                self.logger.warning(t"Failed to delete command '{discord_command_id}': {result}")
                continue
            self._drop_row(session, discord_command_id)

    @staticmethod
    def _drop_row(session: Session, discord_command_id: str) -> None:
        """Delete the synced row for ``discord_command_id``, if any."""
        row = _locked_row(session, discord_command_id)
        if row is not None:
            session.delete(row)
            session.commit()
