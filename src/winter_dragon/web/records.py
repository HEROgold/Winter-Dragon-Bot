"""What the dashboard shows of the bot: the features its cogs define, and every record it stores about a member.

The records come from the lifecycle tables' :class:`~wd_db.extension.lifecycle.Ownership`, the same rule a deletion
request follows, so the data page lists exactly what deleting would remove.
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from sqlalchemy import func
lazy from sqlmodel import Session, select
lazy from wd_bot.cogs import GroupCog
lazy from wd_db.extension.lifecycle import owned_by
lazy from wd_db.schema import ensure_tables

lazy from winter_dragon import cogs
lazy from winter_dragon.cogs.privacy import DeletionRequest, stored_models
lazy from winter_dragon.cogs.reminder import REMINDER_TABLES
lazy from winter_dragon.web.formatting import humanized_name, plural, shown_value


if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from wd_db.extension.lifecycle import LifecycleModel
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
    for cog in sorted(groups, key=lambda group: group.group_name):
        yield Feature(name=cog.group_name, description=cog.group_description)


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


def member_records(bind: Engine, member_id: int) -> Generator[DataRecord]:
    """Yield a record for every table holding rows the member ``member_id`` owns, by name."""
    models = sorted(stored_models(bind), key=lambda model: model.__name__)
    with Session(bind) as session:
        for model in models:
            count = session.exec(select(func.count()).select_from(owned_by(model, member=member_id).subquery())).one()
            if count:
                yield DataRecord(model=model, count=count)


def record_table(bind: Engine, member_id: int, key: str, zone: ZoneInfo) -> RecordTable | None:
    """Return the rows the member ``member_id`` owns in the table ``key``, times in ``zone``; ``None`` for no such table."""
    model = next((model for model in stored_models(bind) if model.__table__.name == key), None)
    if model is None:
        return None
    fields = tuple(name for name in model.model_fields if name not in HIDDEN_FIELDS)
    with Session(bind) as session:
        rows = tuple(
            tuple(shown_value(getattr(row, name), zone) for name in fields)
            for row in session.exec(owned_by(model, member=member_id))
        )
    return RecordTable(columns=tuple(humanized_name(name) for name in fields), rows=rows)
