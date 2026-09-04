"""Startup errors for the bot."""
from __future__ import annotations

from wd_errors import BaseError


class StartupError(BaseError, RuntimeError):
    """Raised when the bot fails to start up properly."""
