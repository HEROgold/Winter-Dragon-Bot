"""Settings for personal reminders."""

from __future__ import annotations

lazy from .config import Config


class ReminderSettings:
    """How often due reminders are looked for."""

    check_interval = Config(60)
    """Seconds between two looks for due reminders; a reminder arrives at most this late."""
