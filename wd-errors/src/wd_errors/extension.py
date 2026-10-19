"""Module that contains extension related errors."""
from __future__ import annotations

lazy from wd_errors import BaseError


class ExtensionError(BaseError):
    """Raised when an extension fails to load."""

    def __init__(self, extension: str, original_exception: Exception) -> None:
        """Initialize the ExtensionFailed error."""
        self.extension = extension
        self.original_exception = original_exception
        super().__init__(f"Failed to load extension {extension}: {original_exception}")

    def __str__(self) -> str:
        return f"Failed to load extension {self.extension}: {self.original_exception}"
