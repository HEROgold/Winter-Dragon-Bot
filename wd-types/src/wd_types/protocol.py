"""Contains protocols for WinterDragon."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Mentionable(Protocol):
    """A protocol for objects that can be mentioned in Discord."""

    @property
    def mention(self) -> str:
        """Return the string that can be used to mention this object."""
        ...

