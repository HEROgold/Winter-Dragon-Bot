"""The reminders page: a member's reminders by day, and adding or removing one, as ``/reminder`` does in Discord."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum, auto
lazy from datetime import UTC, date, datetime, time, timedelta
lazy from itertools import groupby
lazy from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Form
lazy from fastapi import Request, status
lazy from sqlalchemy import Engine  # noqa: TC002 - FastAPI resolves route annotations at runtime
lazy from sqlmodel import Session
lazy from starlette.responses import Response  # noqa: TC002 - FastAPI resolves route annotations at runtime
lazy from wd_db.extension.lifecycle import create_or_restore, soft_delete
lazy from wd_types.clock import utc_now

lazy from winter_dragon.cogs.reminder import (
    AnyReminder,
    Reminder,
    ReminderSettings,
    TimedReminder,
    choice_value,
    find_reminder,
    owned_reminders,
)
lazy from winter_dragon.web.accounts import Account, checked_csrf, signed_in, visitor_zone
lazy from winter_dragon.web.formatting import day_label, every
lazy from winter_dragon.web.responses import database, is_htmx, render, see_other


if TYPE_CHECKING:
    from collections.abc import Generator
    from zoneinfo import ZoneInfo


router = APIRouter(prefix="/reminders")


class Repeat(StrEnum):
    """How often a reminder added on the page comes back."""

    NEVER = auto()
    DAILY = auto()
    WEEKLY = auto()
    EVERY_DAYS = auto()
    """Every :attr:`ReminderDraft.every_days` days."""


class InvalidReminderError(ValueError):
    """The add form describes a reminder that can't be set; the message says why, for the person who filled it in."""


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

    def reminder(self, user_id: int, zone: ZoneInfo, now: datetime) -> AnyReminder:
        """Return the reminder this draft describes for the user ``user_id``, read in ``zone`` and checked against ``now``.

        Raises:
            InvalidReminderError: the text, the time or the repeat is out of what ``/reminder`` accepts.

        """
        content = self.content.strip()
        if not content:
            msg = "Write what to remind you of."
            raise InvalidReminderError(msg)
        if len(content) > ReminderSettings.max_content_length:
            msg = f"Keep your reminder under {ReminderSettings.max_content_length} characters."
            raise InvalidReminderError(msg)
        due = self._due(zone)
        if not now < due <= now + timedelta(days=ReminderSettings.max_delay_days):
            msg = f"Pick a time between now and {ReminderSettings.max_delay_days} days from now."
            raise InvalidReminderError(msg)
        interval = self._interval()
        if interval is None:
            return Reminder(content=content, user_id=user_id, timestamp=due)
        return TimedReminder(content=content, user_id=user_id, timestamp=due, repeat_every=interval)

    def _due(self, zone: ZoneInfo) -> datetime:
        try:
            local = datetime.combine(date.fromisoformat(self.day), time.fromisoformat(self.at))
        except ValueError:
            msg = "Pick a date and a time."
            raise InvalidReminderError(msg) from None
        return local.replace(tzinfo=zone).astimezone(UTC)

    def _interval(self) -> timedelta | None:
        match self.repeat:
            case Repeat.NEVER:
                return None
            case Repeat.DAILY:
                return timedelta(days=1)
            case Repeat.WEEKLY:
                return timedelta(weeks=1)
            case Repeat.EVERY_DAYS:
                if not self.every_days.isdigit() or not 1 <= int(self.every_days) <= ReminderSettings.max_delay_days:
                    msg = f"Repeat every 1 to {ReminderSettings.max_delay_days} days."
                    raise InvalidReminderError(msg)
                return timedelta(days=int(self.every_days))


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
        return choice_value(self.reminder)

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


def reminder_days(bind: Engine, user_id: int, zone: ZoneInfo, now: datetime) -> Generator[ReminderDay]:
    """Yield the user ``user_id``'s reminders grouped by the day they're due in ``zone``, soonest first."""
    with Session(bind) as session:
        stops = [ReminderStop(reminder, zone) for reminder in owned_reminders(session, user_id)]
    stops.sort(key=lambda stop: stop.reminder.timestamp)
    today = now.astimezone(zone).date()
    for day, stops_on_day in groupby(stops, key=lambda stop: stop.due.date()):
        yield ReminderDay(label=day_label(day, today), stops=tuple(stops_on_day))


def _page(  # noqa: PLR0913 - the form's state is part of what's rendered
    request: Request,
    account: Account,
    bind: Engine,
    draft: ReminderDraft | None = None,
    *,
    template: str | None = None,
    error: str | None = None,
    status_code: int = 200,
) -> Response:
    """Render the reminders page, or the part of it ``template`` names for an htmx swap."""
    zone, now = visitor_zone(request), utc_now()
    return render(
        request,
        template or "reminders/page.html",
        status_code=status_code,
        days=list(reminder_days(bind, account.id, zone, now)),
        draft=draft or blank_draft(zone, now),
        error=error,
        zone_name=zone.key,
        max_length=ReminderSettings.max_content_length,
        repeats=Repeat,
    )


@router.get("")
def reminders_page(
    request: Request,
    account: Annotated[Account, Depends(signed_in)],
    bind: Annotated[Engine, Depends(database)],
) -> Response:
    """Show the signed-in member's reminders and the form to add one."""
    return _page(request, account, bind)


@router.post("", dependencies=[Depends(checked_csrf)])
def add_reminder(  # noqa: PLR0913 - one parameter per form field
    request: Request,
    account: Annotated[Account, Depends(signed_in)],
    bind: Annotated[Engine, Depends(database)],
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
    board = "reminders/_board.html" if is_htmx(request) else None
    try:
        reminder = draft.reminder(account.id, visitor_zone(request), utc_now())
    except InvalidReminderError as refused:
        return _page(
            request,
            account,
            bind,
            draft,
            template=board,
            error=str(refused),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    with Session(bind) as session:
        create_or_restore(session, reminder)
        session.commit()
    if board is None:
        return see_other(router.prefix)
    return _page(request, account, bind, template=board)


@router.post("/{key}/delete", dependencies=[Depends(checked_csrf)])
def remove_reminder(
    request: Request,
    key: str,
    account: Annotated[Account, Depends(signed_in)],
    bind: Annotated[Engine, Depends(database)],
) -> Response:
    """Remove the signed-in member's reminder ``key``; someone else's, or one already gone, is left be."""
    with Session(bind) as session:
        found = find_reminder(session, account.id, key)
        if found is not None:
            soft_delete(session, found)
            session.commit()
    if not is_htmx(request):
        return see_other(router.prefix)
    return _page(request, account, bind, template="reminders/_list.html")
