"""What the dashboard shows of the bot: the features its cogs define, and every record it stores about a member.

The records come from the lifecycle tables' :class:`~wd_db.extension.lifecycle.Ownership` and the rows each
:class:`~winter_dragon.member_hidden.MemberHiddenHook` removes, the same rules a deletion request follows, so the data
page lists exactly what deleting would remove.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

lazy from sqlalchemy import func
lazy from sqlmodel import Session, col, select
lazy from wd_bot.cogs import GroupCog
lazy from wd_db.schema import ensure_tables

lazy from winter_dragon import cogs
lazy from winter_dragon.cogs.privacy.domain import (
    DeletionRequest,
    HiddenEntry,
    category_rows,
    removable_only,
    removable_rows,
    restorable_rows,
    stored_models,
)
lazy from winter_dragon.cogs.reminder.domain import REMINDER_TABLES
lazy from winter_dragon.data_categories import DataCategory
lazy from winter_dragon.web.formatting import humanized_name, plural, shown_value


if TYPE_CHECKING:
    from collections.abc import Generator, Iterable
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from sqlalchemy import Engine
    from sqlmodel.sql.expression import SelectOfScalar
    from wd_db.extension.lifecycle import LifecycleModel
    from wd_discord.snowflake import Snowflake


DOCS_URL = "https://herogold.github.io/Winter-Dragon-Bot"
"""Where the documentation site lives, the same address as ``site_url`` in ``zensical.toml``."""

HIDDEN_FIELDS = frozenset(("id", "updated_at", "deleted_at"))
"""Columns of a record the data page leaves out: internal keys and bookkeeping, not the member's data."""


def create_dashboard_tables(bind: Engine) -> None:
    """Make sure the tables the dashboard writes to exist (deletion requests, deleted entries, reminders), as the cogs do."""
    ensure_tables(bind, DeletionRequest, HiddenEntry, *REMINDER_TABLES)


@dataclass(frozen=True)
class Feature:
    """A command group the bot offers: ``/name``, and what it does."""

    name: str
    description: str

    @property
    def docs_url(self) -> str:
        """The address of this group's page on the documentation site."""
        return f"{DOCS_URL}/commands/{self.name}/"


def features() -> Generator[Feature]:
    """Yield every command group the app's cogs define, by name; call :func:`~winter_dragon.cogs.import_cogs` first."""
    pending, groups = list(GroupCog.__subclasses__()), list[type[GroupCog]]()
    while pending:
        cog = pending.pop()
        pending.extend(cog.__subclasses__())
        if cog.__module__.startswith(f"{cogs.__name__}."):
            groups.append(cog)
    for cog in sorted(groups, key=lambda group: group.group_definition.name):
        yield Feature(name=cog.group_definition.name, description=cog.group_definition.description)


@dataclass(frozen=True)
class DataRecord:
    """One table's worth of what the bot stores about a member: which table, and how many rows."""

    model: type[LifecycleModel]
    count: int

    @property
    def key(self) -> str:
        """The table's name, which the page asks for the rows by."""
        return self.model.__table__.name

    @property
    def name(self) -> str:
        """The table's name in words."""
        return humanized_name(self.model.__name__)

    @property
    def summary(self) -> str:
        """How many rows there are, in words."""
        return plural(self.count, "entry")

    @property
    def category(self) -> str:
        """The name of the feature the table belongs to."""
        return DataCategory.of(self.model)


@dataclass(frozen=True)
class RecordGroup:
    """The records of one feature, as the data page groups them."""

    name: str
    records: tuple[DataRecord, ...]

    @property
    def summary(self) -> str:
        """How many rows the feature's tables hold, in words."""
        return plural(sum(record.count for record in self.records), "entry")


@dataclass(frozen=True)
class RecordRow:
    """One row of a record: its ID, which its checkbox names, and its values as the page shows them."""

    id: int
    values: tuple[str, ...]


@dataclass(frozen=True)
class RecordTable:
    """The rows of one :class:`DataRecord`, as the data page shows them."""

    key: str
    columns: tuple[str, ...]
    rows: tuple[RecordRow, ...]


def member_records(bind: Engine, member_id: Snowflake) -> Generator[DataRecord]:
    """Yield a record for every table holding rows a deletion request by the member ``member_id`` removes, by name."""
    stored = stored_models(bind)
    with Session(bind) as session:
        for model in sorted(stored, key=lambda model: model.__name__):
            listed = removable_rows(model, member_id, stored)
            count = session.exec(select(func.count()).select_from(listed.subquery())).one()
            if count:
                yield DataRecord(model=model, count=count)


def _grouped(records: Iterable[DataRecord]) -> Generator[RecordGroup]:
    """Yield ``records`` grouped by feature, features by name, keeping the records' order within each."""
    by_feature: dict[str, list[DataRecord]] = {}
    for record in records:
        by_feature.setdefault(record.category, []).append(record)
    for name in sorted(by_feature):
        yield RecordGroup(name=name, records=tuple(by_feature[name]))


def record_groups(bind: Engine, member_id: Snowflake) -> Generator[RecordGroup]:
    """Yield the member ``member_id``'s records grouped by feature, features and tables by name."""
    yield from _grouped(member_records(bind, member_id))


def hidden_groups(bind: Engine, member_id: Snowflake, now: datetime) -> Generator[RecordGroup]:
    """Yield the rows the member ``member_id`` deleted and can still restore at ``now``, grouped like :func:`record_groups`."""
    restorable = restorable_rows(bind, member_id, now)
    by_name = sorted(restorable.items(), key=lambda item: item[0].__name__)
    yield from _grouped(DataRecord(model=model, count=len(ids)) for model, ids in by_name)


def _record_table[M: LifecycleModel](bind: Engine, model: type[M], rows: SelectOfScalar[M], zone: ZoneInfo) -> RecordTable:
    """Return the rows ``rows`` selects of ``model`` as the data page shows them, times in ``zone``."""
    fields = tuple(name for name in model.model_fields if name not in HIDDEN_FIELDS)
    with Session(bind) as session:
        shown = tuple(
            RecordRow(id=row.id or 0, values=tuple(shown_value(getattr(row, name), zone) for name in fields))
            for row in session.exec(rows)
        )
    return RecordTable(key=model.__table__.name, columns=tuple(humanized_name(name) for name in fields), rows=shown)


def record_table(bind: Engine, member_id: Snowflake, key: str, zone: ZoneInfo) -> RecordTable | None:
    """Return the rows of the table ``key`` a deletion request by the member ``member_id`` removes, times in ``zone``.

    ``None`` for no such table.
    """
    stored = stored_models(bind)
    model = next((model for model in stored if model.__table__.name == key), None)
    if model is None:
        return None
    return _record_table(bind, model, removable_rows(model, member_id, stored), zone)


def hidden_table(bind: Engine, member_id: Snowflake, key: str, zone: ZoneInfo, now: datetime) -> RecordTable | None:
    """Return the rows of the table ``key`` the member ``member_id`` can restore at ``now``, times in ``zone``.

    ``None`` when they can restore none of it.
    """
    restorable = restorable_rows(bind, member_id, now)
    model = next((model for model in restorable if model.__table__.name == key), None)
    if model is None:
        return None
    return _record_table(bind, model, select(model).where(col(model.id).in_(restorable[model])), zone)


@dataclass(frozen=True)
class Selection:
    """What a member ticked on the data page: whole features by name, and single rows as ``table:id``."""

    categories: frozenset[str]
    rows: frozenset[str]


def chosen_rows(bind: Engine, member_id: Snowflake, selection: Selection) -> dict[type[LifecycleModel], set[int]]:
    """Return the IDs, by table, of the rows ``selection`` names: every row of each ticked feature, and each ticked row.

    A ticked row of an unknown table, a malformed one, or one a deletion request by the member wouldn't remove
    (someone else's, or already hidden) is left out, so the confirmation counts only what deleting removes.
    """
    chosen = category_rows(bind, member_id, selection.categories)
    by_key = {model.__table__.name: model for model in stored_models(bind)}
    for ticked in selection.rows:
        key, _, row_id = ticked.rpartition(":")
        if key in by_key and row_id.isdigit():
            chosen.setdefault(by_key[key], set()).add(int(row_id))
    return removable_only(bind, member_id, chosen)


def chosen_hidden_rows(
    bind: Engine,
    member_id: Snowflake,
    selection: Selection,
    now: datetime,
) -> dict[type[LifecycleModel], set[int]]:
    """Return the IDs, by table, of the restorable rows ``selection`` names: all of each ticked feature, and each row.

    Only rows the member ``member_id`` can restore at ``now`` count; anything else ticked is left out.
    """
    chosen = {
        model: {
            row_id
            for row_id in ids
            if DataCategory.of(model) in selection.categories or f"{model.__table__.name}:{row_id}" in selection.rows
        }
        for model, ids in restorable_rows(bind, member_id, now).items()
    }
    return {model: ids for model, ids in chosen.items() if ids}


def chosen_summary(chosen: dict[type[LifecycleModel], set[int]]) -> list[tuple[str, str]]:
    """Return each feature in ``chosen`` with how many rows of it are chosen, in words, features by name."""
    counts: dict[str, int] = {}
    for model, ids in chosen.items():
        name = DataCategory.of(model)
        counts[name] = counts.get(name, 0) + len(ids)
    return [(name, plural(counts[name], "entry")) for name in sorted(counts)]
