"""How the dashboard writes stored values for people: times in their zone, intervals and table names in words."""

from datetime import date, datetime, timedelta
lazy import re
lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from zoneinfo import ZoneInfo


_WORD_START = re.compile(r"(?<!^)(?=[A-Z])")
_UNITS = (
    ("week", timedelta(weeks=1)),
    ("day", timedelta(days=1)),
    ("hour", timedelta(hours=1)),
    ("minute", timedelta(minutes=1)),
)


def humanized_name(name: str) -> str:
    """Return a class or field name as words: ``TimedReminder`` is ``Timed reminder``, ``repeat_every`` ``Repeat every``."""
    return _WORD_START.sub(" ", name).replace("_", " ").capitalize()


def plural(count: int, noun: str) -> str:
    """Return ``count`` with ``noun``, plural unless there's one: ``1 entry``, ``3 entries``, ``2 reminders``."""
    if count == 1:
        return f"1 {noun}"
    return f"{count} {noun[:-1]}ies" if noun.endswith("y") else f"{count} {noun}s"


def every(interval: timedelta) -> str:
    """Return how often something repeating every ``interval`` happens: ``Every day``, ``Every 3 days``."""
    for unit, length in _UNITS:
        if interval >= length and interval % length == timedelta(0):
            count = interval // length
            return f"Every {unit}" if count == 1 else f"Every {count} {unit}s"
    return f"Every {int(interval.total_seconds())} seconds"


def day_label(day: date, today: date) -> str:
    """Return ``day`` as a heading on ``today``: ``Today``, ``Tomorrow``, or ``Tuesday 21 October`` (with any other year)."""
    if day == today:
        return "Today"
    if day == today + timedelta(days=1):
        return "Tomorrow"
    label = f"{day:%A} {day.day} {day:%B}"
    return label if day.year == today.year else f"{label} {day.year}"


def shown_value(value: object, zone: ZoneInfo) -> str:
    """Return a stored ``value`` as the data page shows it: times in ``zone``, intervals in words, nothing as a dash."""
    match value:
        case None:
            return "—"
        case bool():
            return "Yes" if value else "No"
        case datetime():
            local = value.astimezone(zone)
            return f"{local.day} {local:%b %Y, %H:%M}"
        case timedelta():
            return every(value)
        case _:
            return str(value)
