"""The privacy tables, and the rules for hiding a member's or a guild's data, for the privacy cog and the dashboard.

Deleting a record only soft-deletes it, so it can still be restored for :data:`RETENTION`; after that it's purged.
"""

from datetime import date, datetime, timedelta
lazy from dataclasses import KW_ONLY, dataclass
lazy from enum import StrEnum, auto
lazy from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import DiscordKeyedModel, LifecycleModel, Ownership
lazy from sqlalchemy import inspect, or_
lazy from sqlmodel import Session, SQLModel, col
lazy from wd_db.extension.lifecycle import DELETED_MEMBER, alive, lifecycle_models, owned_by, soft_delete

lazy from winter_dragon.data_categories import DataCategory
lazy from winter_dragon.member_hidden import MemberHiddenHook


if TYPE_CHECKING:
    lazy from collections.abc import Collection, Generator, Iterable, Mapping

    lazy from sqlalchemy import Connection, Engine
    lazy from sqlmodel.sql.expression import SelectOfScalar
    lazy from wd_discord.snowflake import Snowflake


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
    guild_id: Snowflake | None
    day: date
    count: int


PRIVACY_TABLES = (DepartedGuild, DeletionRequest, CommandUsage)
"""Every privacy table, which the privacy cog creates on load."""


DataCategory("Command usage", (CommandUsage,))


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
    member: Snowflake | None = None,
    guild: Snowflake | None = None,
) -> None:
    """Soft-delete at ``now`` every alive row of ``models`` owned by ``member`` and/or ``guild``."""
    for model in models:
        for row in session.exec(owned_by(model, member=member, guild=guild)).all():
            soft_delete(session, row, at=now)


def anonymise_member(session: Session, models: Iterable[type[LifecycleModel]], member_id: Snowflake) -> None:
    """Replace ``member_id`` with :data:`~wd_db.extension.lifecycle.DELETED_MEMBER` in every alive row's anonymised columns."""
    for model in models:
        for name in model.anonymised:
            for row in session.exec(alive(model).where(getattr(model, name) == int(member_id))).all():
                setattr(row, name, DELETED_MEMBER)
                session.add(row)


def hide_member_data(bind: Engine | Connection, member_id: Snowflake, now: datetime) -> bool:
    """Hide all of the member ``member_id``'s data at ``now``, for their deletion request; ``False`` if it was already.

    That's every row a member owns, also those a guild owns too, after every registered
    :class:`~winter_dragon.member_hidden.MemberHiddenHook` cleaned up its feature. Columns a model lists as
    anonymised get the member's ID replaced instead, and their rows stay alive. Does nothing while an earlier
    request is hidden but not purged yet; one that never got hidden (hiding failed) is hidden now. What the member
    stores afterwards is new data, which this request leaves be.
    """
    models = stored_models(bind)
    with Session(bind) as session:
        request = session.get(DeletionRequest, int(member_id))
        if request is not None and request.hidden_at is not None and request.purged_at is None:
            return False
        if request is None or request.purged_at is not None:
            request = request or DeletionRequest(id=int(member_id), requested_at=now)
            request.requested_at, request.hidden_at, request.purged_at = now, None, None
            session.add(request)
            session.commit()
        MemberHiddenHook.run_all(session, member_id, models)
        anonymise_member(session, models, member_id)
        hide_owned(session, models, now, member=member_id)
        request.hidden_at = now
        session.add(request)
        session.commit()
    return True


def removable_rows[M: LifecycleModel](
    model: type[M],
    member_id: Snowflake,
    stored: Collection[type[LifecycleModel]],
) -> SelectOfScalar[M]:
    """Select the ``model`` rows a deletion request by ``member_id`` removes: owned, hook-removed and anonymised rows."""
    owned = owned_by(model, member=member_id)
    hooked = [rows.ids for rows in MemberHiddenHook.removed_by_all(member_id, stored) if rows.model is model]
    anonymised = [
        alive(model).where(getattr(model, name) == int(member_id)).with_only_columns(col(model.id)) for name in model.anonymised
    ]
    if not hooked and not anonymised:
        return owned
    ids = (owned.with_only_columns(col(model.id)), *hooked, *anonymised)
    return alive(model).where(or_(*(col(model.id).in_(selected) for selected in ids)))


def _removable_ids(
    session: Session,
    model: type[LifecycleModel],
    member_id: Snowflake,
    stored: Collection[type[LifecycleModel]],
) -> set[int]:
    """Return the IDs of the ``model`` rows a deletion request by ``member_id`` removes."""
    return {row.id for row in session.exec(removable_rows(model, member_id, stored)) if row.id is not None}


def removable_only(
    bind: Engine | Connection,
    member_id: Snowflake,
    chosen: Mapping[type[LifecycleModel], Collection[int]],
) -> dict[type[LifecycleModel], set[int]]:
    """Return ``chosen`` (IDs by table) with only the rows a deletion request by ``member_id`` removes."""
    stored = stored_models(bind)
    with Session(bind) as session:
        kept = {
            model: _removable_ids(session, model, member_id, stored) & {int(row_id) for row_id in ids}
            for model, ids in chosen.items()
            if model in stored
        }
    return {model: ids for model, ids in kept.items() if ids}


def category_rows(
    bind: Engine | Connection,
    member_id: Snowflake,
    names: Collection[str],
) -> dict[type[LifecycleModel], set[int]]:
    """Return the IDs of every row a deletion request by ``member_id`` removes, in the tables of the categories ``names``."""
    stored = stored_models(bind)
    with Session(bind) as session:
        chosen = {
            model: _removable_ids(session, model, member_id, stored) for model in stored if DataCategory.of(model) in names
        }
    return {model: ids for model, ids in chosen.items() if ids}


def _anonymise_row(row: LifecycleModel, member_id: Snowflake) -> bool:
    """Replace ``member_id`` with :data:`~wd_db.extension.lifecycle.DELETED_MEMBER` in ``row``'s anonymised columns.

    Return whether any column named the member.
    """
    named = [name for name in row.anonymised if getattr(row, name) == int(member_id)]
    for name in named:
        setattr(row, name, DELETED_MEMBER)
    return bool(named)


def hide_member_rows(
    bind: Engine | Connection,
    member_id: Snowflake,
    chosen: Mapping[type[LifecycleModel], Collection[int]],
    now: datetime,
) -> int:
    """Hide the rows ``chosen`` (IDs by table) of the member ``member_id``'s data at ``now``, as a deletion request would.

    Only rows a deletion request by the member removes count; any other ID is ignored, so a member can't hide someone
    else's data. Each feature's :class:`~winter_dragon.member_hidden.MemberHiddenHook` cleans up the rows it knows
    first, such as leaving a team, which hands its captaincy over. Of the rest, a row the member doesn't own but whose
    anonymised column names them keeps living with the member's ID replaced; every other row is soft-deleted, and
    purged :data:`RETENTION` later. Return how many of the chosen rows were hidden or anonymised.
    """
    stored = stored_models(bind)
    done = 0
    with Session(bind) as session:
        for model in purge_order(model for model in chosen if model in stored):
            ids = _removable_ids(session, model, member_id, stored) & {int(row_id) for row_id in chosen[model]}
            done += len(ids)
            ids -= MemberHiddenHook.rows_hidden_all(session, member_id, model, ids, stored)
            session.flush()
            owned = {row.id for row in session.exec(owned_by(model, member=member_id).where(col(model.id).in_(ids)))}
            for row in session.exec(alive(model).where(col(model.id).in_(ids))).all():
                if row.id in owned or not _anonymise_row(row, member_id):
                    soft_delete(session, row, at=now)
                else:
                    session.add(row)
        session.commit()
    return done


def deletion_steps(bind: Engine | Connection, member_id: Snowflake) -> Generator[tuple[DeletionStep, datetime]]:
    """Yield the steps the member ``member_id``'s deletion request got through, with when, in order."""
    if DeletionRequest not in stored_models(bind):
        return
    with Session(bind) as session:
        request = session.get(DeletionRequest, int(member_id))
        if request is not None:
            yield from request.steps
