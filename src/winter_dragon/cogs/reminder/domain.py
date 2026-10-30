"""The reminder tables, their queries, and the rules a new reminder must meet, for ``/reminder`` and the dashboard alike."""

from datetime import datetime, timedelta
lazy from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field, Session, col
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import LifecycleModel, Ownership
lazy from wd_db.extension.lifecycle import owned_by
lazy from wd_errors import Refused

lazy from winter_dragon.config import CogConfig


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from wd_discord.snowflake import Snowflake


SECONDS_PER_UNIT = {"minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800}


class ReminderSettings:
    """Settings for reminders, in their ``cogs.ini`` section."""

    check_interval = CogConfig(60)
    """Seconds between two looks for due reminders; a reminder arrives at most this late."""
    max_delay_days = CogConfig(3650)
    """Days ahead a reminder may be set, or a repeating one may wait between reminders."""
    max_content_length = CogConfig(1000)
    """The longest reminder text accepted, keeping the reminder DM well within Discord's message limit."""


class ReminderBase(LifecycleModel):
    """What one-off and repeating reminders share; ``user_id`` is the Discord user to remind, who owns it."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id")

    content: str
    user_id: int = Field(sa_type=BigInteger, index=True)
    timestamp: datetime = Field(sa_type=AwareDateTime)
    """When the reminder is due next."""


class Reminder(ReminderBase, table=True):
    """A reminder sent once, then soft-deleted."""


class TimedReminder(ReminderBase, table=True):
    """A reminder sent again every :attr:`repeat_every`, until removed."""

    repeat_every: timedelta


type AnyReminder = Reminder | TimedReminder

REMINDER_TABLES = (Reminder, TimedReminder)
"""Every reminder table, which the reminder cog and the dashboard create."""


def _max_delay() -> timedelta:
    return timedelta(days=ReminderSettings.max_delay_days)


def delay_from(**amounts: int) -> timedelta:
    """Return the delay made of ``amounts`` per unit (``minutes=5, hours=1``), for :func:`new_reminder` to check.

    Adds whole seconds as integers first and keeps the result within a second of the allowed range, so an absurd
    amount is refused rather than overflowing ``timedelta``.
    """
    seconds = sum(SECONDS_PER_UNIT[unit] * amount for unit, amount in amounts.items())
    return timedelta(seconds=min(max(seconds, 0), _max_delay().total_seconds() + 1))


def new_reminder(
    content: str,
    user_id: Snowflake,
    due: datetime,
    now: datetime,
    repeat_every: timedelta | None = None,
) -> AnyReminder | Refused:
    """Return the reminder of ``content`` for ``user_id``, due at ``due``, or why it can't be set at ``now``.

    The text is stripped and must be non-empty and at most :attr:`ReminderSettings.max_content_length` long; ``due``
    must lie after ``now`` and at most :attr:`ReminderSettings.max_delay_days` days later. With ``repeat_every`` it's a
    :class:`TimedReminder`, whose interval must be at least a minute and at most that many days.
    """
    content, days = content.strip(), ReminderSettings.max_delay_days
    if not content:
        return Refused("Write what to remind you of.")
    if len(content) > ReminderSettings.max_content_length:
        return Refused(f"Keep your reminder under {ReminderSettings.max_content_length} characters.")
    if not now < due <= now + _max_delay():
        return Refused(f"Pick a time between now and {days} days from now.")
    if repeat_every is None:
        return Reminder(content=content, user_id=int(user_id), timestamp=due)
    if not timedelta(minutes=1) <= repeat_every <= _max_delay():
        return Refused(f"Pick a repeat between 1 minute and {days} days.")
    return TimedReminder(content=content, user_id=int(user_id), timestamp=due, repeat_every=repeat_every)


def next_occurrence(due: datetime, repeat_every: timedelta, now: datetime) -> datetime:
    """Return the first time after ``now`` that a reminder due at ``due`` and repeating every ``repeat_every`` is due.

    Skips the occurrences missed while the bot was offline, instead of sending each of them.
    """
    missed = (now - due) // repeat_every if now >= due else -1
    return due + repeat_every * (missed + 1)


def reminder_message(content: str) -> str:
    """Return the DM reminding someone of ``content``."""
    return f"I'm here to remind you about\n`{content}`"


def owned_reminders(session: Session, user_id: Snowflake) -> Generator[AnyReminder]:
    """Yield every reminder of the user ``user_id``: repeating ones first, then one-off ones by when they're due."""
    yield from session.exec(owned_by(TimedReminder, member=user_id))
    yield from session.exec(owned_by(Reminder, member=user_id).order_by(col(Reminder.timestamp)))
