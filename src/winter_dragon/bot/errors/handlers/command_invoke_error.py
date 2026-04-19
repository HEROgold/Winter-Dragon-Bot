"""Handler for CommandInvokeError - catches unhandled exceptions in commands."""

from __future__ import annotations

from discord.app_commands.errors import CommandInvokeError

from .base import BaseError


class AppCommandInvokeError(BaseError, error_type=CommandInvokeError):
    """Handler for CommandInvokeError - catches all unhandled exceptions in app commands."""

    error_title = "❌ An Error Occurred"
    error_description = "An unexpected error occurred while executing this command."
