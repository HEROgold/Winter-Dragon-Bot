"""Sort a Discord payload into a table's columns, its child lists and the rest (kept as custom data).

A payload key lands in, by the first rule that matches:

1. a child list, when the table declares the key in ``children`` (a single object counts as a one-item list);
2. the column of the same name, or the one ``renames`` gives it;
3. ``<key>_<subkey>`` columns, for a nested object; subkeys without a column stay in the custom data;
4. the custom data.

Values are converted to their column's type (Discord IDs arrive as strings, timestamps as ISO strings).
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import TypeDecorator

from archive.models.base import ArchiveChild, ArchiveEntity


if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy import Column
    from sqlalchemy.sql.base import ReadOnlyColumnCollection

    from archive.models.base import ArchiveTable


TIMESTAMPS = frozenset({"created_at", "updated_at", "deleted_at"})
"""Every table's own timestamps; a payload key of the same name is never written into them."""
CHILD_BOOKKEEPING = frozenset({"owner_id", "parent_id", "position"})
"""A child row's place in its payload; on other tables these are ordinary Discord fields (a channel's position)."""


@dataclass
class Split:
    """A payload sorted for one table."""

    values: dict[str, Any] = field(default_factory=dict)
    """Column values, converted to the column's type."""
    children: dict[str, list[Any]] = field(default_factory=dict)
    """The child lists, by payload key."""
    extra: dict[str, Any] = field(default_factory=dict)
    """Everything without a column."""


def split(table: type[ArchiveTable], payload: Mapping[str, Any]) -> Split:
    """Sort ``payload`` into ``table``'s columns, child lists and custom data."""
    result = Split()
    for key, value in payload.items():
        if key in table.children:
            result.children[key] = _as_list(value)
        elif (column := column_for(table, key)) is not None:
            result.values[column] = convert(_columns(table)[column], value)
        elif isinstance(value, dict):
            _flatten(table, key, value, result)
        else:
            result.extra[key] = value
    return result


def column_for(table: type[ArchiveTable], key: str) -> str | None:
    """Return the column ``table`` stores payload ``key`` in, or ``None`` when it has none."""
    columns = _columns(table)
    writable = set(columns.keys()) - _bookkeeping(table)
    renamed = table.renames.get(key)
    if renamed is not None and renamed in writable:
        return renamed
    return key if key in writable else None


def convert(column: Column[Any], value: object) -> Any:  # noqa: ANN401 - whatever the column stores
    """Convert a JSON ``value`` to what ``column`` stores."""
    if value is None:
        return None
    kind = _python_type(column)
    if kind is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    if kind is bool:
        return bool(value)
    if kind in (int, float):
        return kind(str(value))
    if kind is str and not isinstance(value, str):
        return _text(value)
    return value


def _bookkeeping(table: type[ArchiveTable]) -> frozenset[str]:
    """Return the columns of ``table`` the archive sets itself: an entity's ``id`` is its Discord ID, others' isn't."""
    if issubclass(table, ArchiveEntity):
        return TIMESTAMPS
    if issubclass(table, ArchiveChild):
        return TIMESTAMPS | CHILD_BOOKKEEPING | {"id"}
    return TIMESTAMPS | {"id"}


def _python_type(column: Column[Any]) -> type:
    """Return the Python type ``column`` stores; ``object`` when its type doesn't say (JSON)."""
    sql_type = column.type
    if isinstance(sql_type, TypeDecorator):
        sql_type = sql_type.impl_instance
    try:
        return sql_type.python_type
    except NotImplementedError:
        return object


def _text(value: object) -> str:
    """Return ``value`` as a string column stores it: numbers as digits, anything else as JSON."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return json.dumps(value)


def _flatten(table: type[ArchiveTable], key: str, value: dict[str, Any], result: Split) -> None:
    """Store nested object ``value`` in ``<key>_<subkey>`` columns; the subkeys without one go to the custom data."""
    columns = _columns(table)
    rest = {}
    for subkey, subvalue in value.items():
        column = column_for(table, f"{key}_{subkey}")
        if column is None or isinstance(subvalue, (dict, list)):
            rest[subkey] = subvalue
        else:
            result.values[column] = convert(columns[column], subvalue)
    if rest:
        result.extra[key] = rest


def _as_list(value: object) -> list[Any]:
    """Return a child list's items: ``None`` is none, a single object is one."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _columns(table: type[ArchiveTable]) -> ReadOnlyColumnCollection[str, Column[Any]]:
    """Return ``table``'s columns by name."""
    return table.__table__.columns
