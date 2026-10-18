"""Privacy: soft-deleted records are purged for good once they've been deleted for :data:`RETENTION`.

Deleting a record only soft-deletes it, so it can still be restored for a while. Once a day this cog hard-deletes
every soft-deleted row of every lifecycle table older than that, so "deleted" turns into "gone" on schedule.

A guild that removes the bot has all its data hidden; re-adding the bot within :data:`RETENTION` brings exactly that
data back, and after that it's purged like any other soft-deleted row. A member who asks for their data to be
deleted has all of it hidden at once, and purged :data:`RETENTION` later; that can't be undone.

Each application command run is counted per member, command, guild and UTC day, in one place for every cog; counts
are kept for :data:`USAGE_RETENTION`.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
lazy import asyncio
lazy from dataclasses import KW_ONLY, dataclass
lazy from enum import StrEnum, auto
lazy from typing import TYPE_CHECKING, ClassVar, override

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import DiscordKeyedModel, LifecycleModel, Ownership
lazy from sqlalchemy import delete, inspect
lazy from sqlalchemy.exc import SQLAlchemyError
lazy from sqlmodel import Session, SQLModel, col, select
lazy from wd_bot.cogs import Cog
lazy from wd_db.extension.lifecycle import alive, create_or_restore, lifecycle_models, owned_by, soft_delete
lazy from wd_discord import CommandInteraction
lazy from wd_discord.gateway import EventName
lazy from wd_discord.interactions import ApplicationCommandOptionType
lazy from wd_types.clock import utc_now

lazy from winter_dragon.cogs.tournament.models import Tournament
lazy from winter_dragon.cogs.tournament.service import open_signups_of, withdraw


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Iterable

    lazy from sqlalchemy import Connection, Engine
    lazy from wd_discord import AnyInteraction, GatewayGuild, GuildDelete


RETENTION = timedelta(days=30)
"""How long a soft-deleted record can still be restored before it's purged for good."""
PURGE_INTERVAL = timedelta(days=1)
"""How often the purge runs."""
USAGE_RETENTION = timedelta(days=365)
"""How long command usage counts are kept, alive or not."""


class DepartedGuild(DiscordKeyedModel, table=True):
    """A guild that removed the bot, whose data is hidden until it's back or purged; ``id`` is the guild's.

    Owned by no one, so hiding the guild's data leaves it be.
    """

    departed_at: datetime = Field(sa_type=AwareDateTime)


class DeletionStep(StrEnum):
    """How far a member's deletion request got, in order."""

    REQUESTED = auto()
    HIDDEN = auto()
    """All the member's data is soft-deleted."""
    PURGED = auto()
    """:data:`RETENTION` passed, so the member's data is purged for good."""


class DeletionRequest(DiscordKeyedModel, table=True):
    """A member's request to delete all their data, and when each :class:`DeletionStep` was done; ``id`` is the member's.

    Owned by no one, so the deletion it records leaves it be; it's kept once purged, to show the request finished.
    """

    requested_at: datetime = Field(sa_type=AwareDateTime)
    hidden_at: datetime | None = Field(default=None, sa_type=AwareDateTime)
    purged_at: datetime | None = Field(default=None, sa_type=AwareDateTime)

    @property
    def steps(self) -> Generator[tuple[DeletionStep, datetime]]:
        """Yield each step done so far with when it was done, in order."""
        done = (
            (DeletionStep.REQUESTED, self.requested_at),
            (DeletionStep.HIDDEN, self.hidden_at),
            (DeletionStep.PURGED, self.purged_at),
        )
        yield from ((step, at) for step, at in done if at is not None)


class CommandUsage(LifecycleModel, table=True):
    """How often a member ran a command in a guild on one UTC day; the member owns it, so a departing guild leaves it."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id")
    natural_key: ClassVar[tuple[str, ...]] = ("user_id", "command", "guild_id", "day")

    user_id: int = Field(sa_type=BigInteger, index=True)
    command: str
    """The command's full name, with its group and subcommand: ``reminder add``."""
    guild_id: int | None = Field(default=None, sa_type=BigInteger)
    """``None`` for a direct message."""
    day: date
    uses: int = 0


@dataclass(frozen=True)
class UsageCount:
    """How often a member ran ``command`` in the guild ``guild_id`` (``None`` for a DM) on ``day``."""

    _: KW_ONLY
    command: str
    guild_id: int | None
    day: date
    count: int


def command_path(interaction: CommandInteraction) -> str:
    """Return the full name of the command ``interaction`` ran, with its group and subcommand: ``reminder add``."""
    subcommands = (ApplicationCommandOptionType.SUB_COMMAND_GROUP, ApplicationCommandOptionType.SUB_COMMAND)
    names, options = [interaction.command_name], interaction.options
    while (chosen := next((option for option in options if option.type in subcommands), None)) is not None:
        names.append(chosen.name)
        options = chosen.options or []
    return " ".join(names)


PRIVACY_TABLES = (DepartedGuild, DeletionRequest, CommandUsage)
"""Every table the privacy cog creates on load."""


def purge_order(models: Iterable[type[LifecycleModel]]) -> list[type[LifecycleModel]]:
    """Return ``models`` children first: a table that points at another (by foreign key) comes before it."""
    rank = {table.name: index for index, table in enumerate(SQLModel.metadata.sorted_tables)}
    return sorted(models, key=lambda model: rank[model.__table__.name], reverse=True)


def stored_models(bind: Engine | Connection) -> list[type[LifecycleModel]]:
    """Return every lifecycle model whose table exists in ``bind``, children first.

    Call it before opening a session: inspecting borrows a connection, which on a single-connection pool (sqlite in
    memory) rolls back that session's pending writes when it's returned.
    """
    existing = set(inspect(bind).get_table_names())
    return [model for model in purge_order(lifecycle_models()) if model.__table__.name in existing]


def hide_owned(
    session: Session,
    models: Iterable[type[LifecycleModel]],
    now: datetime,
    *,
    member: int | None = None,
    guild: int | None = None,
) -> None:
    """Soft-delete at ``now`` every alive row of ``models`` owned by ``member`` and/or ``guild``."""
    for model in models:
        for row in session.exec(owned_by(model, member=member, guild=guild)).all():
            soft_delete(session, row, at=now)


def hide_member_data(bind: Engine | Connection, member_id: int, now: datetime) -> bool:
    """Hide all of the member ``member_id``'s data at ``now``, for their deletion request; ``False`` if it was already.

    That's every row a member owns, also those a guild owns too, and their sign-up to each tournament that hasn't
    started, by the rule ``/tournament leave`` follows. Does nothing while an earlier request is hidden but not
    purged yet; one that never got hidden (hiding failed) is hidden now. What the member stores afterwards is new
    data, which this request leaves be.
    """
    models = stored_models(bind)
    with Session(bind) as session:
        request = session.get(DeletionRequest, member_id)
        if request is not None and request.hidden_at is not None and request.purged_at is None:
            return False
        if request is None or request.purged_at is not None:
            request = request or DeletionRequest(id=member_id, requested_at=now)
            request.requested_at, request.hidden_at, request.purged_at = now, None, None
            session.add(request)
            session.commit()
        if Tournament in models:
            for tournament in list(open_signups_of(session, member_id)):
                withdraw(session, tournament, member_id)
        hide_owned(session, models, now, member=member_id)
        request.hidden_at = now
        session.add(request)
        session.commit()
    return True


def deletion_steps(bind: Engine | Connection, member_id: int) -> Generator[tuple[DeletionStep, datetime]]:
    """Yield the steps the member ``member_id``'s deletion request got through, with when, in order."""
    if DeletionRequest not in stored_models(bind):
        return
    with Session(bind) as session:
        request = session.get(DeletionRequest, member_id)
        if request is not None:
            yield from request.steps


class Privacy(Cog):
    """Purges soft-deleted records daily, and hides the data of departed guilds and of members who asked."""

    _task: asyncio.Task[None] | None = None

    @override
    async def load(self) -> None:
        """Create the privacy tables, then start the background task purging soft-deleted records."""
        self.create_tables(*PRIVACY_TABLES)
        self._task = self.bot.loop.create_task(self._run())

    @override
    async def unload(self) -> None:
        """Stop the background task."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        await super().unload()

    async def _run(self) -> None:
        """Purge every :data:`PURGE_INTERVAL`, forever; a failing pass is logged and the next one runs as usual."""
        while True:
            try:
                await self.purge(utc_now())
            except Exception:
                self.logger.exception(t"Purging soft-deleted records failed")
            await asyncio.sleep(PURGE_INTERVAL.total_seconds())

    @staticmethod
    def _departure(session: Session, guild_id: int) -> DepartedGuild | None:
        """Return the guild's departure that isn't over yet, if any."""
        return session.exec(alive(DepartedGuild).where(DepartedGuild.id == guild_id)).first()

    # --- Departed guilds ---------------------------------------------------------------------------------------------

    @Cog.listener(EventName.GUILD_DELETE)
    async def on_guild_delete(self, event: GuildDelete) -> None:
        """Hide the data of a guild that removed the bot; a guild that only went offline keeps it."""
        if event.unavailable:
            return
        guild_id, now, models = int(event.guild.id), utc_now(), stored_models(self.bind)
        with Session(self.bind) as session:
            if self._departure(session, guild_id) is not None:
                return
            create_or_restore(session, DepartedGuild(id=guild_id, departed_at=now))
            hide_owned(session, models, now, guild=guild_id)
            session.commit()
        self.logger.info(t"Guild {guild_id} removed the bot; hid its data")

    @Cog.listener(EventName.GUILD_CREATE)
    async def on_guild_create(self, guild: GatewayGuild) -> None:
        """Bring back the data a guild had when it removed the bot, if it's back within :data:`RETENTION`.

        Only rows hidden at or after the departure come back; what the guild deleted before it stays deleted, and so
        do the rows of members who asked for deletion since.
        """
        guild_id, now, models = int(guild.id), utc_now(), stored_models(self.bind)
        with Session(self.bind) as session:
            departure = self._departure(session, guild_id)
            if departure is None:
                return
            if now - departure.departed_at < RETENTION:
                self._restore_guild(session, models, guild_id, departure.departed_at)
                self.logger.info(t"Guild {guild_id} is back; restored its data")
            soft_delete(session, departure, at=now)
            session.commit()

    @staticmethod
    def _restore_guild(session: Session, models: Iterable[type[LifecycleModel]], guild_id: int, departed_at: datetime) -> None:
        """Restore the guild's rows hidden since ``departed_at``, except those of members who asked for deletion since."""
        asked_since = select(DeletionRequest.id).where(col(DeletionRequest.requested_at) >= departed_at)
        deleted_members = list(session.exec(asked_since))
        for model in models:
            withheld = {
                row.id
                for member_id in deleted_members
                for row in session.exec(owned_by(model, member=member_id, guild=guild_id, include_deleted=True))
            }
            hidden = owned_by(model, guild=guild_id, include_deleted=True).where(col(model.deleted_at) >= departed_at)
            for row in session.exec(hidden).all():
                if row.id not in withheld:
                    row.deleted_at = None
                    session.add(row)

    # --- Member deletion requests ------------------------------------------------------------------------------------

    async def request_deletion(self, member_id: int, now: datetime) -> None:
        """Hide all of the member ``member_id``'s data at ``now`` (:func:`hide_member_data`); :meth:`purge` deletes it later."""
        if hide_member_data(self.bind, member_id, now):
            self.logger.info(t"Member {member_id} asked for their data to be deleted; hid it")

    def deletion_steps(self, member_id: int) -> Generator[tuple[DeletionStep, datetime]]:
        """Yield the steps the member ``member_id``'s deletion request got through, with when, in order."""
        yield from deletion_steps(self.bind, member_id)

    # --- Command usage ---------------------------------------------------------------------------------------------------

    @Cog.listener(EventName.INTERACTION_CREATE)
    async def on_interaction(self, interaction: AnyInteraction) -> None:
        """Count a run of an application command; autocomplete and component interactions don't count.

        A count that can't be stored is logged; the command itself runs apart from this, so it never fails over it.
        """
        if not isinstance(interaction, CommandInteraction) or interaction.user is None:
            return
        user_id, command = int(interaction.user.id), command_path(interaction)
        guild_id = None if interaction.guild is None else int(interaction.guild.id)
        try:
            self._count(user_id, command, guild_id, utc_now().date())
        except SQLAlchemyError as error:
            self.logger.warning(t"Could not count /{command} for member {user_id}: {error}")

    def _count(self, user_id: int, command: str, guild_id: int | None, day: date) -> None:
        """Add one to the member's count of ``command`` in the guild on ``day``."""
        with Session(self.bind) as session:
            same_key = (
                CommandUsage.user_id == user_id,
                CommandUsage.command == command,
                CommandUsage.guild_id == guild_id,
                CommandUsage.day == day,
            )
            usage = session.exec(alive(CommandUsage).where(*same_key)).first()
            if usage is None:
                create_or_restore(session, CommandUsage(user_id=user_id, command=command, guild_id=guild_id, day=day, uses=1))
            else:
                usage.uses += 1
                session.add(usage)
            session.commit()

    def usage(self, member_id: int) -> Generator[UsageCount]:
        """Yield the member ``member_id``'s command usage counts, day by day."""
        with Session(self.bind) as session:
            counts = owned_by(CommandUsage, member=member_id).order_by(col(CommandUsage.day), col(CommandUsage.command))
            for row in session.exec(counts):
                yield UsageCount(command=row.command, guild_id=row.guild_id, day=row.day, count=row.uses)

    # --- Purging -----------------------------------------------------------------------------------------------------

    async def purge(self, now: datetime) -> None:
        """Hard-delete every lifecycle row soft-deleted more than :data:`RETENTION` before ``now``, children first.

        Departures older than :data:`RETENTION` are over: their records are removed, so the guild comes back empty.
        Deletion requests older than that get their :attr:`DeletionStep.PURGED` step, and command usage counts older
        than :data:`USAGE_RETENTION` are deleted, alive or not. Each row is deleted on its own,
        so one that fails (a row still pointing at it, say) is logged and skipped while the rest go. Running it again
        at the same ``now`` deletes nothing more.
        """
        cutoff, models = now - RETENTION, stored_models(self.bind)
        if DepartedGuild in models:
            self._end_departures(now, cutoff)
        if DeletionRequest in models:
            self._finish_deletion_requests(now, cutoff)
        if CommandUsage in models:
            with Session(self.bind) as session:
                session.exec(delete(CommandUsage).where(col(CommandUsage.day) < (now - USAGE_RETENTION).date()))
                session.commit()
        for model in models:
            self._purge_table(model, cutoff)

    def _end_departures(self, now: datetime, cutoff: datetime) -> None:
        """Remove the records of departures before ``cutoff``."""
        with Session(self.bind) as session:
            for departure in session.exec(alive(DepartedGuild).where(col(DepartedGuild.departed_at) < cutoff)).all():
                soft_delete(session, departure, at=now)
            session.commit()

    def _finish_deletion_requests(self, now: datetime, cutoff: datetime) -> None:
        """Record the purged step of the deletion requests made before ``cutoff``."""
        with Session(self.bind) as session:
            unfinished = col(DeletionRequest.purged_at).is_(None), col(DeletionRequest.requested_at) < cutoff
            for request in session.exec(select(DeletionRequest).where(*unfinished)).all():
                request.purged_at = now
                session.add(request)
            session.commit()

    def _purge_table(self, model: type[LifecycleModel], cutoff: datetime) -> None:
        """Hard-delete ``model``'s rows soft-deleted before ``cutoff``, one at a time."""
        with Session(self.bind) as session:
            expired = session.exec(select(model.id).where(col(model.deleted_at) < cutoff)).all()
        for row_id in expired:
            with Session(self.bind) as session:
                row = session.get(model, row_id)
                if row is None:
                    continue
                session.delete(row)
                try:
                    session.commit()
                except SQLAlchemyError as error:
                    self.logger.warning(t"Could not purge {model.__name__} {row_id}: {error}")
