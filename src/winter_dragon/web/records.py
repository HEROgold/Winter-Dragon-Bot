"""What the dashboard shows of the bot: the features its cogs define, and every record it stores about a member.

The records come from the lifecycle tables' :class:`~wd_db.extension.lifecycle.Ownership` and the rows each
:class:`~winter_dragon.member_hidden.MemberHiddenHook` removes, the same rules a deletion request follows, so the data
page lists exactly what deleting would remove.
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from sqlalchemy import func, or_
lazy from sqlmodel import Session, col, select
lazy from wd_bot.cogs import GroupCog
lazy from wd_db.extension.lifecycle import alive, owned_by
lazy from wd_db.schema import ensure_tables

lazy from winter_dragon import cogs
lazy from winter_dragon.cogs.privacy.domain import DeletionRequest, stored_models
lazy from winter_dragon.cogs.reminder.domain import REMINDER_TABLES
lazy from winter_dragon.member_hidden import MemberHiddenHook
lazy from winter_dragon.web.formatting import humanized_name, plural, shown_value


if TYPE_CHECKING:
    from collections.abc import Collection, Generator

    from sqlalchemy import Engine
    from sqlmodel.sql.expression import SelectOfScalar
    from wd_db.extension.lifecycle import LifecycleModel
    from wd_discord.snowflake import Snowflake
    from zoneinfo import ZoneInfo


HIDDEN_FIELDS = frozenset(("id", "updated_at", "deleted_at"))
"""Columns of a record the data page leaves out: internal keys and bookkeeping, not the member's data."""


def create_dashboard_tables(bind: Engine) -> None:
    """Make sure the tables the dashboard writes to exist (deletion requests and reminders), as the bot's cogs do."""
    ensure_tables(bind, DeletionRequest, *REMINDER_TABLES)


@dataclass(frozen=True)
class Feature:
    """A command group the bot offers: ``/name``, and what it does."""

    name: str
    description: str


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


@dataclass(frozen=True)
class RecordTable:
    """The rows of one :class:`DataRecord`, as the data page shows them."""

    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


def _removed_by_deletion[M: LifecycleModel](
    model: type[M],
    member_id: Snowflake,
    stored: Collection[type[LifecycleModel]],
) -> SelectOfScalar[M]:
    """Select the ``model`` rows a deletion request by ``member_id`` removes: those they own, and those a hook removes."""
    owned = owned_by(model, member=member_id)
    hooked = [rows.ids for rows in MemberHiddenHook.removed_by_all(member_id, stored) if rows.model is model]
    if not hooked:
        return owned
    ids = (owned.with_only_columns(col(model.id)), *hooked)
    return alive(model).where(or_(*(col(model.id).in_(selected) for selected in ids)))


def member_records(bind: Engine, member_id: Snowflake) -> Generator[DataRecord]:
    """Yield a record for every table holding rows a deletion request by the member ``member_id`` removes, by name."""
    stored = stored_models(bind)
    with Session(bind) as session:
        for model in sorted(stored, key=lambda model: model.__name__):
            listed = _removed_by_deletion(model, member_id, stored)
            count = session.exec(select(func.count()).select_from(listed.subquery())).one()
            if count:
                yield DataRecord(model=model, count=count)


def record_table(bind: Engine, member_id: Snowflake, key: str, zone: ZoneInfo) -> RecordTable | None:
    """Return the rows of the table ``key`` a deletion request by the member ``member_id`` removes, times in ``zone``.

    ``None`` for no such table.
    """
    stored = stored_models(bind)
    model = next((model for model in stored if model.__table__.name == key), None)
    if model is None:
        return None
    fields = tuple(name for name in model.model_fields if name not in HIDDEN_FIELDS)
    with Session(bind) as session:
        rows = tuple(
            tuple(shown_value(getattr(row, name), zone) for name in fields)
            for row in session.exec(_removed_by_deletion(model, member_id, stored))
        )
    return RecordTable(columns=tuple(humanized_name(name) for name in fields), rows=rows)
