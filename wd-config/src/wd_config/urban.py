"""Settings for the Urban Dictionary lookup."""

from __future__ import annotations

lazy from .config import Config


class UrbanSettings:
    """Which Urban Dictionary lookups are allowed, and how much of a result is shown."""

    allow_random = Config(default=True)
    """Whether /urban random may be used; random definitions are often not safe for work."""
    max_definitions = Config(5)
    """How many definitions one reply shows at most."""
