"""Module for the Error handler."""

from herogold.log import LoggerMixin

from .error import DiscordError


GLOBAL = "GLOBAL"


class ErrorHandler(LoggerMixin):
    """Class for handling Errors."""

    def __init__(self, error: DiscordError) -> None:
        """Initialize the Error handler."""
        self.error = error

    async def handle(self) -> None:
        """Handle the Error."""
        self.logger.debug(f"Handling {self.error.command_error.__class__.__name__}")
        await self.error.handle()
