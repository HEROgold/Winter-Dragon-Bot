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
lazy from sqlalchemy import inspect
lazy from sqlmodel import Session, SQLModel
lazy from wd_db.extension.lifecycle import lifecycle_models, owned_by, soft_delete

lazy from winter_dragon.member_hidden import MemberHiddenHook


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Iterable

    lazy from sqlalchemy import Connection, Engine
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


def hide_member_data(bind: Engine | Connection, member_id: Snowflake, now: datetime) -> bool:
    """Hide all of the member ``member_id``'s data at ``now``, for their deletion request; ``False`` if it was already.

    That's every row a member owns, also those a guild owns too, after every registered
    :class:`~winter_dragon.member_hidden.MemberHiddenHook` cleaned up its feature. Does nothing while an earlier
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
        hide_owned(session, models, now, member=member_id)
        request.hidden_at = now
        session.add(request)
        session.commit()
    return True


def deletion_steps(bind: Engine | Connection, member_id: Snowflake) -> Generator[tuple[DeletionStep, datetime]]:
    """Yield the steps the member ``member_id``'s deletion request got through, with when, in order."""
    if DeletionRequest not in stored_models(bind):
        return
    with Session(bind) as session:
        request = session.get(DeletionRequest, int(member_id))
        if request is not None:
            yield from request.steps
