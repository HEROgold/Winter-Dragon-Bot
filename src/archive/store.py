"""Write sorted payloads to the archive tables: upsert an entity, append an event, soft-delete, replace child lists.

Everything happens in the caller's session; the caller commits.
"""

from typing import TYPE_CHECKING, Any, cast

from sqlmodel import and_, col, select
from wd_db.extension.custom_data import get_custom_data, set_custom_data
from wd_types.clock import utc_now

from archive.mapping import Split, convert, split
from archive.models.base import ArchiveChild, ArchiveCompositeEntity, ArchiveEntity


if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlmodel import Session
    from wd_db.extension.lifecycle import LifecycleModel

    from archive.models.base import ArchiveEvent


type Entity = ArchiveEntity | ArchiveCompositeEntity


def upsert[E: Entity](session: Session, table: type[E], payload: Mapping[str, Any], **known: object) -> E:
    """Write ``payload`` onto ``table``'s stored row, creating it, or restoring it when deleted; return the row.

    Only the fields in ``payload`` (and ``known``, which wins) are written, so a partial payload never erases the
    others. A child list in the payload replaces the stored one; custom data is merged key by key.
    """
    part = split(table, payload)
    part.values.update(known)
    row = _stored(session, table, part.values)
    if row is None:
        row = table(**part.values)
    else:
        for name, value in part.values.items():
            setattr(row, name, value)
        row.deleted_at = None
    session.add(row)
    session.flush()
    for key, items in part.children.items():
        child_table = table.children[key]
        _delete_children(session, child_table, _id(row))
        _write_children(session, child_table, items, owner_id=_id(row), parent_id=_id(row))
    if part.extra:
        set_custom_data(session, row, get_custom_data(session, row) | part.extra)
    return row


def append[V: ArchiveEvent](session: Session, table: type[V], payload: Mapping[str, Any], **known: object) -> V:
    """Append ``payload`` to ``table`` as a new row, with ``known`` columns set; return the row."""
    part = split(table, payload)
    part.values.update(known)
    row = table(**part.values)
    session.add(row)
    session.flush()
    for key, items in part.children.items():
        _write_children(session, table.children[key], items, owner_id=_id(row), parent_id=_id(row))
    if part.extra:
        set_custom_data(session, row, part.extra)
    return row


def soft_delete(session: Session, table: type[Entity], **key: object) -> None:
    """Mark the stored row with ``key`` (its ``id``, or its natural key) deleted; nothing happens when there is none."""
    row = _stored(session, table, {name: convert(table.__table__.columns[name], value) for name, value in key.items()})
    if row is not None and row.deleted_at is None:
        row.deleted_at = utc_now()
        session.add(row)


def _stored[E: Entity](session: Session, table: type[E], values: Mapping[str, Any]) -> E | None:
    """Return the stored row, alive or deleted, that ``values`` identify."""
    if issubclass(table, ArchiveEntity):
        return cast("E | None", session.get(table, values["id"]))
    key = and_(*(col(getattr(table, name)) == values[name] for name in table.natural_key))
    return session.exec(select(table).where(key)).first()


def _write_children(
    session: Session,
    table: type[ArchiveChild],
    items: list[Any],
    *,
    owner_id: int,
    parent_id: int,
) -> None:
    """Add ``items`` as ``table`` rows under ``parent_id``, and their own child lists under each of them."""
    for position, item in enumerate(items):
        part = split(table, item) if isinstance(item, dict) else Split(values={table.scalar: item})
        row = table(**part.values, owner_id=owner_id, parent_id=parent_id, position=position)
        session.add(row)
        if not part.children and not part.extra:
            continue
        session.flush()
        for key, grandchildren in part.children.items():
            _write_children(session, table.children[key], grandchildren, owner_id=owner_id, parent_id=_id(row))
        if part.extra:
            set_custom_data(session, row, part.extra)


def _delete_children(session: Session, table: type[ArchiveChild], owner_id: int, seen: frozenset[type] = frozenset()) -> None:
    """Delete every ``table`` row of ``owner_id``, the rows of its child tables, and their custom data."""
    if table in seen:
        return
    for row in session.exec(select(table).where(col(table.owner_id) == owner_id)):
        set_custom_data(session, row, {})
        session.delete(row)
    for child_table in table.children.values():
        _delete_children(session, child_table, owner_id, seen | {table})


def _id(row: LifecycleModel) -> int:
    """Return the ``id`` of ``row``, which has been flushed so it has one."""
    return cast("int", row.id)
