"""The one clock: every "now" in the workspace comes from :func:`utc_now`."""

lazy from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)
