"""Handler for CommandNotFound - catches unhandled exceptions in commands."""

from discord.app_commands.errors import CommandNotFound

from .base import BaseError


class CommandNotFoundError(BaseError, error_type=CommandNotFound):
    """Handler for CommandNotFound - catches all unhandled exceptions in app commands."""

    error_title = "❌ Command Not Found"
    error_description = "The command you tried to use was not found."
