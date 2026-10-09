"""Settings for the guild stats channels."""

from __future__ import annotations

lazy from .config import Config


class StatsSettings:
    """How often the stats channels are renamed to show the current counts."""

    update_interval = Config(3600)
    """Seconds between two updates; Discord lets a channel be renamed only twice per 10 minutes, so keep it long."""
