"""Custom confkit data types shared across settings."""

from __future__ import annotations

lazy from typing import Any

lazy from confkit.data_types import BaseDataType

lazy from .config import Config


class Combined(BaseDataType[str]):
    """A data type that combines multiple Config descriptors and literals."""

    def __init__(self, *args: Config[Any] | str | float) -> None:
        """Initialize with Config descriptors and/or literal fragments."""
        super().__init__(default="")
        self.args = args

    def convert(self, value: str) -> str:
        """Convert from a string to the combined data type."""
        return value

    def __str__(self) -> str:
        """Create a full string value from all parts."""
        parts = []
        for arg in self.args:
            match arg:
                case Config():
                    parts.append(str(arg._data_type))  # noqa: SLF001
                case _:
                    parts.append(str(arg))
        return "".join(parts)
