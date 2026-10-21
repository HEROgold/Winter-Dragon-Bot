"""The four kinds of archive table, and the conventions :mod:`archive.mapping` relies on.

Every table is named ``archive_<class>``. Columns are named after the Discord field they hold, so a payload maps
onto a table by name. A one-off nested object is stored as ``<field>_<subfield>`` columns (``assets_large_image``);
a list is stored as rows of a child table, declared in the parent's :attr:`ArchiveTable.children`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import BigInteger, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr
from sqlmodel import JSON, Field
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import DiscordKeyedModel, LifecycleModel


if TYPE_CHECKING:
    from sqlalchemy import Table


def snowflake(*, index: bool = False) -> Any:  # noqa: ANN401 - a pydantic FieldInfo, typed as its column's value
    """Return an optional Discord ID column."""
    return Field(default=None, sa_type=BigInteger, index=index)


def moment() -> Any:  # noqa: ANN401 - a pydantic FieldInfo, typed as its column's value
    """Return an optional timezone-aware timestamp column."""
    return Field(default=None, sa_type=AwareDateTime)


def json_column() -> Any:  # noqa: ANN401 - a pydantic FieldInfo, typed as its column's value
    """Return an optional JSON column (JSONB on PostgreSQL), for a payload kept whole."""
    return Field(default=None, sa_column=Column(JSON().with_variant(JSONB(), "postgresql")))


class ArchiveTable:
    """What :mod:`archive.mapping` reads from every archive table."""

    if TYPE_CHECKING:
        __table__: ClassVar[Table]

    children: ClassVar[dict[str, type[ArchiveChild]]] = {}
    """Payload lists stored as child rows, by payload key."""
    renames: ClassVar[dict[str, str]] = {}
    """Payload keys stored in a column of another name, such as a payload ``id`` that isn't this table's ``id``.

    A rename applies only when the table has the target column; otherwise the key is kept as custom data.
    """

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Prefix every archive table, so it can't clash with a bot table of the same name."""
        return f"archive_{cls.__name__.lower()}"


class ArchiveEntity(ArchiveTable, DiscordKeyedModel):
    """The current state of one Discord object; ``id`` is its Discord ID."""


class ArchiveCompositeEntity(ArchiveTable, LifecycleModel):
    """The current state of an object identified by several Discord IDs (its :attr:`natural_key`), not one."""


class ArchiveEvent(ArchiveTable, LifecycleModel):
    """Something that happened, appended and never changed; ``created_at`` is when the archive received it."""

    renames: ClassVar[dict[str, str]] = {"id": "discord_id"}


class ArchiveChild(ArchiveTable, LifecycleModel):
    """One item of a list inside an archived payload, at ``position`` in that list.

    ``owner_id`` is the ``id`` of the archived row the payload belongs to, so all of a message's embeds, their fields
    and its components can be replaced at once. ``parent_id`` is the ``id`` of the row holding the list: the owner
    itself, or another child row (an embed holds its fields).
    """

    renames: ClassVar[dict[str, str]] = {"id": "discord_id"}
    scalar: ClassVar[str] = "value"
    """The column a list of plain values (role IDs, labels) is stored in."""

    owner_id: int = Field(sa_type=BigInteger, index=True)
    parent_id: int = Field(sa_type=BigInteger)
    position: int
