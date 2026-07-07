"""Module for string utilities."""
from __future__ import annotations

from herogold.errors import with_known_exception
from herogold.protocols import DataDescriptor
from wd_errors.size import TooLongError


class LimitedString(DataDescriptor[str, object]):
    """Descriptor for a string with a maximum length."""

    def __init__(self, max_length: int) -> None:
        """Initialize the descriptor."""
        self.max_length = max_length

    def __set__(self, instance: object, value: str) -> None:
        """Set the value of the descriptor."""
        if not isinstance(value, str):
            msg = f"Expected a string, got {type(value).__name__}."
            raise TypeError(msg)
        if len(value) > self.max_length:
            raise TooLongError(self.max_length, len(value))
        self.value = value

    @with_known_exception(AttributeError)
    def __get__(self, instance: object, owner: type) -> str:
        """Get the value of the descriptor."""
        return self.value

    def __delete__(self, instance: object) -> None:
        """Delete the value of the descriptor."""
        del self.value
        del self.max_length
