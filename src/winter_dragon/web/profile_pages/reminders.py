"""The Profile's reminders page: a member's reminders by day, and adding or removing one, as ``/reminder`` does in Discord."""

from dataclasses import dataclass, replace
from enum import StrEnum, auto
lazy from datetime import UTC, date, datetime, time, timedelta
lazy from itertools import groupby
lazy from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Form
lazy from fastapi import Request, status
lazy from sqlmodel import Session
lazy from starlette.responses import Response  # noqa: TC002 - FastAPI resolves route annotations at runtime
lazy from wd_db.extension.lifecycle import create_or_restore, find_by_key, row_key, soft_delete
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

lazy from winter_dragon.cogs.reminder.domain import (
    REMINDER_TABLES,
    AnyReminder,
    ReminderSettings,
    TimedReminder,
    new_reminder,
    owned_reminders,
)
lazy from winter_dragon.web.accounts import SignedIn, checked_csrf, visitor_zone
lazy from winter_dragon.web.formatting import day_label, every
lazy from winter_dragon.web.profile import ProfileContext, profile_page, render_profile_page
lazy from winter_dragon.web.profile import router as profile_router
lazy from winter_dragon.web.responses import Database, after_post, is_htmx


if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from wd_discord.snowflake import Snowflake
    from zoneinfo import ZoneInfo

    from winter_dragon.web.accounts import Account


router = APIRouter()
SLUG = "reminders"
"""The page's path segment under the Profile: ``/profile/reminders``."""
PATH = f"{profile_router.prefix}/{SLUG}"
"""The page's URL, where a plain form post is sent back to."""
BOARD = "reminders/_board.html"
LIST = "reminders/_list.html"


class Repeat(StrEnum):
    """How often a reminder added on the page comes back."""

    NEVER = auto()
    DAILY = auto()
    WEEKLY = auto()
    EVERY_DAYS = auto()
    """Every :attr:`ReminderDraft.every_days` days."""


@dataclass(frozen=True)
class ReminderDraft:
    """What the add form holds, as typed, so a refused form comes back filled in."""

    content: str = ""
    day: str = ""
    """The date it's due first, ``YYYY-MM-DD`` in the visitor's zone."""
    at: str = "09:00"
    """The time of day it's due, ``HH:MM`` in the visitor's zone."""
    repeat: Repeat = Repeat.NEVER
    every_days: str = "3"

    def reminder(self, user_id: Snowflake, zone: ZoneInfo, now: datetime) -> AnyReminder | Refused:
        """Return the reminder this draft describes for the user ``user_id``, read in ``zone``, or why it can't be set.

        Checked against ``now`` by :func:`~winter_dragon.cogs.reminder.domain.new_reminder`, as ``/reminder`` is.
        """
        try:
            local = datetime.combine(date.fromisoformat(self.day), time.fromisoformat(self.at))
        except ValueError:
            return Refused("Pick a date and a time.")
        return new_reminder(self.content, user_id, local.replace(tzinfo=zone).astimezone(UTC), now, self._interval())

    def _interval(self) -> timedelta | None:
        """Return how often the reminder repeats; one out of range is kept just outside it, for ``new_reminder`` to refuse."""
        match self.repeat:
            case Repeat.NEVER:
                return None
            case Repeat.DAILY:
                return timedelta(days=1)
            case Repeat.WEEKLY:
                return timedelta(weeks=1)
            case Repeat.EVERY_DAYS:
                days = int(self.every_days) if self.every_days.isdigit() else 0
                return timedelta(days=min(days, ReminderSettings.max_delay_days + 1))


def blank_draft(zone: ZoneInfo, now: datetime) -> ReminderDraft:
    """Return an empty add form, due tomorrow morning in ``zone``."""
    return ReminderDraft(day=(now.astimezone(zone).date() + timedelta(days=1)).isoformat())


@dataclass(frozen=True)
class ReminderStop:
    """One reminder on the page, with its due time in the visitor's zone."""

    reminder: AnyReminder
    zone: ZoneInfo

    @property
    def key(self) -> str:
        """The reminder's table and ID, which its delete button posts to."""
        return row_key(self.reminder)

    @property
    def due(self) -> datetime:
        """When it's due next, in the visitor's zone."""
        return self.reminder.timestamp.astimezone(self.zone)

    @property
    def repeat(self) -> str | None:
        """How often it comes back, in words; ``None`` for a one-off."""
        return every(self.reminder.repeat_every) if isinstance(self.reminder, TimedReminder) else None


@dataclass(frozen=True)
class ReminderDay:
    """The reminders due on one day, under its heading."""

    label: str
    stops: tuple[ReminderStop, ...]


def reminder_days(bind: Engine, user_id: Snowflake, zone: ZoneInfo, now: datetime) -> Generator[ReminderDay]:
    """Yield the user ``user_id``'s reminders grouped by the day they're due in ``zone``, soonest first."""
    with Session(bind) as session:
        stops = [ReminderStop(reminder, zone) for reminder in owned_reminders(session, user_id)]
    stops.sort(key=lambda stop: stop.reminder.timestamp)
    today = now.astimezone(zone).date()
    for day, stops_on_day in groupby(stops, key=lambda stop: stop.due.date()):
        yield ReminderDay(label=day_label(day, today), stops=tuple(stops_on_day))


def _context(  # noqa: PLR0913 - the page context takes the form's state as well as the member's
    bind: Engine,
    user_id: Snowflake,
    zone: ZoneInfo,
    now: datetime,
    draft: ReminderDraft | None = None,
    error: str | None = None,
) -> dict[str, object]:
    """Return the template context of the reminders page for the user ``user_id``, with the form ``draft`` filled in."""
    return {
        "days": list(reminder_days(bind, user_id, zone, now)),
        "draft": draft or blank_draft(zone, now),
        "error": error,
        "zone_name": zone.key,
        "max_length": ReminderSettings.max_content_length,
        "repeats": Repeat,
    }


@profile_page(slug=SLUG, title="Reminders", template="profile/reminders.html", router=router)
def reminders(context: ProfileContext) -> dict[str, object]:
    """Return the page's context: the member's reminders and an empty add form, due tomorrow morning."""
    return _context(context.bind, context.member_id, context.zone, utc_now())


def _respond(  # noqa: PLR0913 - the form's state is part of what's rendered
    request: Request,
    account: Account,
    bind: Engine,
    draft: ReminderDraft | None = None,
    *,
    fragment: str = BOARD,
    error: str | None = None,
    status_code: int = 200,
) -> Response:
    """Render the reminders page, or the part of it the template ``fragment`` holds for an htmx swap."""
    zone, now = visitor_zone(request), utc_now()
    context = _context(bind, account.id, zone, now, draft, error)
    return render_profile_page(
        request,
        SLUG,
        context,
        fragment=fragment if is_htmx(request) else None,
        status_code=status_code,
    )


@router.post("", dependencies=[Depends(checked_csrf)])
def add_reminder(  # noqa: PLR0913 - one parameter per form field
    request: Request,
    account: SignedIn,
    bind: Database,
    content: Annotated[str, Form()] = "",
    day: Annotated[str, Form()] = "",
    at: Annotated[str, Form()] = "",
    repeat: Annotated[str, Form()] = Repeat.NEVER,
    every_days: Annotated[str, Form()] = "3",
) -> Response:
    """Add the reminder the form describes, or show the form again with why it can't be set."""
    draft = ReminderDraft(content=content, day=day, at=at, every_days=every_days)
    if repeat in Repeat:
        draft = replace(draft, repeat=Repeat(repeat))
    reminder = draft.reminder(account.id, visitor_zone(request), utc_now())
    if isinstance(reminder, Refused):
        return _respond(
            request,
            account,
            bind,
            draft,
            fragment=BOARD,
            error=reminder.message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    with Session(bind) as session:
        create_or_restore(session, reminder)
        session.commit()
    return after_post(
        request,
        PATH,
        lambda: _respond(request, account, bind, fragment=BOARD),
    )


@router.post("/{key}/delete", dependencies=[Depends(checked_csrf)])
def remove_reminder(
    request: Request,
    key: str,
    account: SignedIn,
    bind: Database,
) -> Response:
    """Remove the signed-in member's reminder ``key``; someone else's, or one already gone, is left be."""
    with Session(bind) as session:
        found = find_by_key(session, REMINDER_TABLES, key)
        if found is not None and found.user_id == int(account.id):
            soft_delete(session, found)
            session.commit()
    return after_post(
        request,
        PATH,
        lambda: _respond(request, account, bind, fragment=LIST),
    )
