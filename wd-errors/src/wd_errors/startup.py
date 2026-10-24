"""Startup errors for the bot."""
lazy from wd_errors import BaseError


class StartupError(BaseError, RuntimeError):
    """Raised when the bot fails to start up properly."""
