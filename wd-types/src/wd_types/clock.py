"""The one clock: every "now" in the workspace comes from :func:`utc_now`."""

from __future__ import annotations

lazy from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)
