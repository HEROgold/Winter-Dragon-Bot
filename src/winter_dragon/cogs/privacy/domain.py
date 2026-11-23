"""The privacy tables, and the rules for hiding a member's or a guild's data, for the privacy cog and the dashboard.

Deleting a record only soft-deletes it, so it can still be restored for :data:`RETENTION`; after that it's purged.
"""

from datetime import date, datetime, timedelta
lazy from dataclasses import KW_ONLY, dataclass, field
lazy from enum import StrEnum, auto
lazy from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import DiscordKeyedModel, LifecycleModel, Ownership
lazy from sqlalchemy import delete, inspect, or_
lazy from sqlalchemy.exc import SQLAlchemyError
lazy from sqlmodel import Session, SQLModel, col, select
lazy from wd_db.extension.lifecycle import DELETED_MEMBER, alive, lifecycle_models, owned_by, soft_delete

from winter_dragon.data_categories import DataCategory
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


class HiddenEntry(LifecycleModel, table=True):
    """A row a member hid from Your data, which they can restore until :data:`RETENTION` after ``hidden_at``.

    Only rows privacy itself soft-deleted are recorded: not an anonymised row, whose member ID is gone, nor one a
    feature's hook dealt with, such as a team the member left. Owned by no one, so the data page doesn't list it; a
    deletion request and the purge delete it outright.
    """

    user_id: int = Field(sa_type=BigInteger, index=True)
    """The member who hid the row."""
    table_name: str
    """The hidden row's table."""
    row_id: int = Field(sa_type=BigInteger)
    """The hidden row's ``id``; a Discord ID in a table keyed by one, so it needs 64 bits."""
    hidden_at: datetime = Field(sa_type=AwareDateTime)


PRIVACY_TABLES = (DepartedGuild, DeletionRequest, CommandUsage, HiddenEntry)
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
        if HiddenEntry in models:  # the request can't be undone, not even the rows the member hid before it
            session.exec(delete(HiddenEntry).where(col(HiddenEntry.user_id) == int(member_id)))
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


@dataclass(frozen=True)
class MemberRowsHidden:
    """What :func:`hide_member_rows` did with the chosen rows."""

    done: int
    """How many were hidden, anonymised or cleaned up by a feature's hook."""
    still_hidden: int = 0
    """How many ``delete_now`` couldn't purge, because another row still points at them; they go with the daily purge."""


def hide_member_rows(
    bind: Engine | Connection,
    member_id: Snowflake,
    chosen: Mapping[type[LifecycleModel], Collection[int]],
    now: datetime,
    *,
    delete_now: bool = False,
) -> MemberRowsHidden:
    """Hide the rows ``chosen`` (IDs by table) of the member ``member_id``'s data at ``now``, as a deletion request would.

    Only rows a deletion request by the member removes count; any other ID is ignored, so a member can't hide someone
    else's data. Each feature's :class:`~winter_dragon.member_hidden.MemberHiddenHook` cleans up the rows it knows
    first, such as leaving a team, which hands its captaincy over. Of the rest, a row the member doesn't own but whose
    anonymised column names them keeps living with the member's ID replaced; every other row is soft-deleted and
    recorded as a :class:`HiddenEntry`, so the member can restore it until it's purged :data:`RETENTION` later.
    ``delete_now`` purges those rows at once instead, and records nothing to restore.
    """
    stored = stored_models(bind)
    done, hidden = 0, dict[type[LifecycleModel], set[int]]()
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
                    hidden.setdefault(model, set()).add(row.id or 0)
                else:
                    session.add(row)
        if not delete_now and HiddenEntry in stored:
            session.add_all(
                HiddenEntry(user_id=int(member_id), table_name=model.__table__.name, row_id=row_id, hidden_at=now)
                for model, ids in hidden.items()
                for row_id in ids
            )
        session.commit()
    if not delete_now:
        return MemberRowsHidden(done=done)
    failed = sum(len(purge_rows(bind, model, ids)) for model, ids in hidden.items())  # children first, as hidden
    return MemberRowsHidden(done=done, still_hidden=failed)


def purge_rows(bind: Engine | Connection, model: type[LifecycleModel], ids: Iterable[int]) -> list[tuple[int, Exception]]:
    """Hard-delete the ``model`` rows ``ids``, each on its own; return the IDs that failed, with why.

    A row fails when another still points at it (by foreign key); the rest go anyway.
    """
    failed: list[tuple[int, Exception]] = []
    for row_id in ids:
        with Session(bind) as session:
            row = session.get(model, row_id)
            if row is None:
                continue
            session.delete(row)
            try:
                session.commit()
            except SQLAlchemyError as error:
                failed.append((row_id, error))
    return failed


def restorable_rows(bind: Engine | Connection, member_id: Snowflake, now: datetime) -> dict[type[LifecycleModel], set[int]]:
    """Return the IDs, by table, of the rows the member ``member_id`` hid that they can still restore at ``now``.

    That's each :class:`HiddenEntry` of theirs younger than :data:`RETENTION` whose row is still hidden.
    """
    stored = stored_models(bind)
    if HiddenEntry not in stored:
        return {}
    by_name = {model.__table__.name: model for model in stored}
    recent = col(HiddenEntry.user_id) == int(member_id), col(HiddenEntry.hidden_at) >= now - RETENTION
    with Session(bind) as session:
        wanted: dict[type[LifecycleModel], set[int]] = {}
        for entry in session.exec(select(HiddenEntry).where(*recent)):
            if entry.table_name in by_name:
                wanted.setdefault(by_name[entry.table_name], set()).add(entry.row_id)
        restorable = {
            model: set(session.exec(select(model.id).where(col(model.id).in_(ids), col(model.deleted_at).is_not(None))))
            for model, ids in wanted.items()
        }
    return {model: {row_id for row_id in ids if row_id is not None} for model, ids in restorable.items() if ids}


def _place_taken(session: Session, row: LifecycleModel) -> bool:
    """Whether an alive row holds ``row``'s :attr:`~wd_db.extension.lifecycle.LifecycleModel.alive_unique` values."""
    model = type(row)
    if not model.alive_unique:
        return False
    same = (getattr(model, name) == getattr(row, name) for name in model.alive_unique)
    return session.exec(alive(model).where(*same)).first() is not None


@dataclass
class _Restoring:
    """One restore by a member: the rows they may bring back, and those that came back so far, by table."""

    session: Session
    restorable: Mapping[type[LifecycleModel], set[int]]
    by_name: Mapping[str, type[LifecycleModel]]
    """Every stored lifecycle model by table name, to follow a foreign key to its parent."""
    back: dict[type[LifecycleModel], set[int]] = field(default_factory=dict)

    def _parents(self, row: LifecycleModel) -> Generator[tuple[type[LifecycleModel], int]]:
        """Yield the table and ID of each row ``row`` points at by foreign key."""
        for key in type(row).__table__.foreign_keys:
            parent = self.by_name.get(key.column.table.name)
            parent_id = getattr(row, key.parent.name)
            if parent is not None and key.column.name == "id" and parent_id is not None:
                yield parent, parent_id

    def _needed(self, model: type[LifecycleModel], row_id: int, needed: dict[type[LifecycleModel], set[int]]) -> bool:
        """Add the ``model`` row ``row_id`` to ``needed`` if it's hidden, with the hidden rows it points at.

        Return whether all of them can come back: each is one the member may restore, and no new row took its place.
        """
        if row_id in needed.get(model, set()) or row_id in self.back.get(model, set()):
            return True
        row = self.session.get(model, row_id)
        if row is None:
            return False
        if row.deleted_at is None:
            return True
        if row_id not in self.restorable.get(model, set()) or _place_taken(self.session, row):
            return False
        needed.setdefault(model, set()).add(row_id)  # before its parents, so keys pointing in a circle end
        return all(self._needed(parent, parent_id, needed) for parent, parent_id in self._parents(row))

    def bring_back(self, model: type[LifecycleModel], row_id: int) -> None:
        """Restore the ``model`` row ``row_id`` with the hidden rows it points at, or none of them if one can't come back.

        So a restored row never points at a hidden one.
        """
        if row_id not in self.restorable.get(model, set()):
            return
        needed: dict[type[LifecycleModel], set[int]] = {}
        if not self._needed(model, row_id, needed):
            return
        for table, ids in needed.items():
            for row in self.session.exec(select(table).where(col(table.id).in_(ids))):
                row.deleted_at = None
                self.session.add(row)
            self.back.setdefault(table, set()).update(ids)
        self.session.flush()


def restore_member_rows(
    bind: Engine | Connection,
    member_id: Snowflake,
    chosen: Mapping[type[LifecycleModel], Collection[int]],
    now: datetime,
) -> int:
    """Bring back the rows ``chosen`` (IDs by table) the member ``member_id`` hid; return how many came back.

    Only :func:`restorable_rows` count, so a member can't restore someone else's rows, nor their own once purged. A
    hidden row a chosen row points at by foreign key comes back with it when the member hid it too; otherwise the
    chosen row stays hidden, as does one whose place a new row took (an alive row with the same unique values).
    """
    stored = stored_models(bind)
    restorable = restorable_rows(bind, member_id, now)
    with Session(bind) as session:
        restoring = _Restoring(session, restorable, {model.__table__.name: model for model in stored})
        for model, ids in chosen.items():
            for row_id in {int(row_id) for row_id in ids}:
                restoring.bring_back(model, row_id)
        for model, ids in restoring.back.items():
            session.exec(
                delete(HiddenEntry).where(
                    col(HiddenEntry.user_id) == int(member_id),
                    col(HiddenEntry.table_name) == model.__table__.name,
                    col(HiddenEntry.row_id).in_(ids),
                ),
            )
        session.commit()
    return sum(len(ids) for ids in restoring.back.values())


def deletion_steps(bind: Engine | Connection, member_id: Snowflake) -> Generator[tuple[DeletionStep, datetime]]:
    """Yield the steps the member ``member_id``'s deletion request got through, with when, in order."""
    if DeletionRequest not in stored_models(bind):
        return
    with Session(bind) as session:
        request = session.get(DeletionRequest, int(member_id))
        if request is not None:
            yield from request.steps
