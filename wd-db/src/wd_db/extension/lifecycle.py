"""The lifecycle every bot table follows: timestamps, soft delete, create-or-restore and a declared owner.

A deleted record is soft-deleted: :func:`soft_delete` stamps its ``deleted_at`` and every read goes through
:func:`alive` (or the model's default ``query``), so the record isn't present anywhere. Creating a record whose key
exists soft-deleted restores it (:func:`create_or_restore`); :func:`upsert` changes the alive one instead, if any.
"""

from dataclasses import dataclass
from datetime import datetime
lazy from typing import TYPE_CHECKING, Any, ClassVar, override

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_types.clock import utc_now
lazy from sqlalchemy import Column, Engine, Index, and_, false, inspect, text, update
lazy from sqlalchemy.orm import declared_attr
lazy from sqlmodel import col, select

from wd_db.extension._herogold import BaseModel
from wd_db.extension.columns import AwareDateTime
lazy from wd_db.errors import AlreadyExistsError


if TYPE_CHECKING:
    lazy from collections.abc import Callable, Generator, Iterable

    lazy from sqlalchemy import Connection
    lazy from sqlmodel import Session
    lazy from sqlmodel.sql.expression import SelectOfScalar


LIFECYCLE_COLUMNS = ("created_at", "updated_at", "deleted_at")
"""The columns every lifecycle table carries, in the order :func:`ensure_lifecycle_columns` adds them."""


@dataclass(frozen=True)
class Through:
    """Ownership inherited from a parent table: ``column`` holds the ``id`` of a ``parent`` row."""

    column: str
    parent: type[LifecycleModel]


@dataclass(frozen=True)
class Ownership:
    """Who a lifecycle table's rows belong to; member deletion and guild departure find rows only through this.

    ``member`` and ``guild`` name the columns holding the owning user's or guild's Discord ID. ``through`` instead
    inherits the parent table's ownership, possibly over several levels. All ``None`` is shared data, owned by no one.
    """

    member: str | None = None
    guild: str | None = None
    through: Through | None = None


class LifecycleModel(BaseModel):
    """The base of every bot table: ``created_at``, ``updated_at`` and ``deleted_at``, all aware UTC.

    ``deleted_at`` is ``None`` while the row is alive. Subclasses declare :attr:`ownership`, and a table keyed by
    several IDs lists them in :attr:`natural_key`, which gets a unique index.
    """

    ownership: ClassVar[Ownership] = Ownership()
    """Who this table's rows belong to; no one by default."""
    natural_key: ClassVar[tuple[str, ...]] = ()
    """Columns that together identify a row besides its ``id``; unique, and matched by :func:`create_or_restore`."""
    alive_unique: ClassVar[tuple[str, ...]] = ()
    """Columns that together are unique among alive rows only, so a soft-deleted row and the one replacing it may share
    them; unlike :attr:`natural_key`, :func:`create_or_restore` doesn't match on them."""

    created_at: datetime = Field(default_factory=utc_now, sa_type=AwareDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=AwareDateTime, sa_column_kwargs={"onupdate": utc_now})
    """Set again on every update."""
    deleted_at: datetime | None = Field(default=None, sa_type=AwareDateTime)
    """When the row was soft-deleted; ``None`` while alive."""

    @override
    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[Index, ...]:
        """Index the alive rows, as herogold's base does, make :attr:`natural_key` unique, and :attr:`alive_unique` unique among alive rows."""
        alive_only = col(cls.deleted_at).is_(None)
        indexes = [Index(f"idx_{cls.__tablename__}_alive_only", "id", postgresql_where=alive_only, sqlite_where=alive_only)]
        if cls.natural_key:
            indexes.append(Index(f"uq_{cls.__tablename__}_natural_key", *cls.natural_key, unique=True))
        if cls.alive_unique:
            name = f"uq_{cls.__tablename__}_alive_unique"
            indexes.append(Index(name, *cls.alive_unique, unique=True, postgresql_where=alive_only, sqlite_where=alive_only))
        return tuple(indexes)


class DiscordKeyedModel(LifecycleModel):
    """A lifecycle model with one row per Discord object, whose ``id`` is that object's Discord ID."""

    id: int = Field(sa_type=BigInteger, primary_key=True, sa_column_kwargs={"autoincrement": False})  # pyrefly: ignore[bad-override] - always given, never generated


def alive[M: LifecycleModel](model: type[M]) -> SelectOfScalar[M]:
    """Return a select of ``model``'s rows that aren't soft-deleted; use it for every read."""
    return select(model).where(col(model.deleted_at).is_(None))


def alive_by_id[M: LifecycleModel](session: Session, model: type[M], record_id: int | None) -> M | None:
    """Return the ``model`` row ``record_id``, unless there's none or it's soft-deleted."""
    return session.exec(alive(model).where(model.id == record_id)).first()


def row_key(row: LifecycleModel) -> str:
    """Return the string naming ``row``: its table and ID, like ``reminder:12``; :func:`find_by_key` reads it back."""
    return f"{type(row).__tablename__}:{row.id}"


def find_by_key[M: LifecycleModel](session: Session, models: Iterable[type[M]], key: str) -> M | None:
    """Return the alive row that :func:`row_key` ``key`` names, if its table is one of ``models``; else ``None``."""
    table, _, row_id = key.partition(":")
    model = next((model for model in models if model.__tablename__ == table), None)
    if model is None or not row_id.isdecimal():
        return None
    return alive_by_id(session, model, int(row_id))


def soft_delete(session: Session, row: LifecycleModel, *, at: datetime | None = None) -> None:
    """Soft-delete ``row``: stamp its ``deleted_at`` with ``at`` (default now), hiding it from :func:`alive`. Caller commits."""
    row.deleted_at = utc_now() if at is None else at
    session.add(row)


def create_or_restore[M: LifecycleModel](session: Session, row: M) -> M:
    """Insert ``row``, or restore the soft-deleted row with the same ``id`` or natural key; return the stored row.

    Restoring clears ``deleted_at`` and overwrites its fields with ``row``'s. The ``id`` is matched first; when no row
    has it, the natural key is, so the stored row may keep its own ``id``. The caller commits.

    Raises:
        AlreadyExistsError: an alive row has the same ``id`` or natural key.

    """
    existing = _same_key(session, row)
    if existing is not None and existing.deleted_at is None:
        msg = f"{type(row).__name__} with the key of {row} already exists."
        raise AlreadyExistsError(msg)
    return _store(session, row, existing)


def upsert[M: LifecycleModel](session: Session, row: M, update: Callable[[M], object] | None = None) -> M:
    """Insert ``row``, or overwrite the stored row (alive or soft-deleted) with the same ``id`` or natural key; return it.

    An alive row is changed by ``update`` when one is given, instead of getting ``row``'s fields. Overwriting clears
    ``deleted_at``. The caller commits.
    """
    existing: M | None = _same_key(session, row)
    if update is not None and existing is not None and existing.deleted_at is None:
        update(existing)
        session.add(existing)
        return existing
    return _store(session, row, existing)


def _store[M: LifecycleModel](session: Session, row: M, existing: M | None) -> M:
    """Add ``row``, or copy its non-key, non-lifecycle fields onto ``existing`` and revive it; return the stored row."""
    if existing is None:
        session.add(row)
        return row
    model: type[M] = type(row)
    for name in model.model_fields:
        if name not in ("id", *LIFECYCLE_COLUMNS):
            setattr(existing, name, getattr(row, name))
    existing.deleted_at = None
    session.add(existing)
    return existing


def _same_key[M: LifecycleModel](session: Session, row: M) -> M | None:
    """Return the stored row, alive or not, with ``row``'s ``id``, else with its natural key."""
    model: type[M] = type(row)
    if row.id is not None and (by_id := session.get(model, row.id)) is not None:
        return by_id
    if not model.natural_key:
        return None
    key = and_(*(getattr(model, name) == getattr(row, name) for name in model.natural_key))
    return session.exec(select(model).where(key)).first()


def owned_by[M: LifecycleModel](
    model: type[M],
    *,
    member: int | None = None,
    guild: int | None = None,
    include_deleted: bool = False,
) -> SelectOfScalar[M]:
    """Return a select of ``model``'s alive rows owned by ``member`` and/or ``guild``, following its :class:`Through` chain.

    Each kind of owner is the column of the nearest table in the chain that declares one, so a row can be owned by
    its own member and, through its parent, by a guild. Matches nothing when no table in the chain declares an owner
    of the asked kind. ``include_deleted`` selects soft-deleted rows too; parents in the chain are never filtered.
    """
    statement = select(model) if include_deleted else alive(model)
    level: type[LifecycleModel] = model
    member_column = guild_column = None
    while True:
        if member_column is None and level.ownership.member is not None:
            member_column = getattr(level, level.ownership.member)
        if guild_column is None and level.ownership.guild is not None:
            guild_column = getattr(level, level.ownership.guild)
        if (through := level.ownership.through) is None:
            break
        statement = statement.join(through.parent, getattr(level, through.column) == through.parent.id)
        level = through.parent
    for column, value in ((member_column, member), (guild_column, guild)):
        if value is not None:
            statement = statement.where(false() if column is None else column == value)
    return statement


def lifecycle_models() -> Generator[type[LifecycleModel]]:
    """Yield every lifecycle model class that is a table."""
    pending: list[type[LifecycleModel]] = [LifecycleModel]
    while pending:
        model = pending.pop()
        pending.extend(model.__subclasses__())
        if getattr(model, "__table__", None) is not None:
            yield model


def ensure_lifecycle_columns(bind: Engine | Connection, *models: type[LifecycleModel]) -> None:
    """Add the lifecycle columns missing from ``models``' existing tables, as an older bot created them.

    ``SQLModel.metadata.create_all`` doesn't alter existing tables. Rows that were already there get ``created_at``
    and ``updated_at`` set to now, and stay alive. The table's missing indexes are created too, among them the alive
    index and the :attr:`LifecycleModel.natural_key` unique index. Tables that don't exist yet are left alone.
    """
    if isinstance(bind, Engine):
        with bind.begin() as connection:
            _add_missing_columns(connection, models)
        return
    _add_missing_columns(bind, models)


def _add_missing_columns(connection: Connection, models: Iterable[type[LifecycleModel]]) -> None:
    inspector = inspect(connection)
    quote = connection.dialect.identifier_preparer.quote
    for model in models:
        table = model.__table__
        if not inspector.has_table(table.name):
            continue
        present = {column["name"] for column in inspector.get_columns(table.name)}
        missing: list[Column[Any]] = [table.c[name] for name in LIFECYCLE_COLUMNS if name not in present]
        for column in missing:
            column_type = column.type.compile(dialect=connection.dialect)
            connection.execute(text(f"ALTER TABLE {quote(table.name)} ADD COLUMN {quote(column.name)} {column_type}"))
        backfill = {column.name: utc_now() for column in missing if column.name != "deleted_at"}
        if backfill:
            connection.execute(update(table).values(backfill))
        indexed = {index["name"] for index in inspector.get_indexes(table.name)}
        for index in table.indexes:
            if index.name not in indexed:
                index.create(connection)
