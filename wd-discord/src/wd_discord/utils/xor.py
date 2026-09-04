"""Generic utilities for the wd-discord package."""
from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from herogold.errors import with_known_exception


if TYPE_CHECKING:
    lazy from herogold.supports import SupportsBool


class XORError(ValueError):
    """Raised when both values are truthy or both values are falsy in an xor operation."""

@with_known_exception(XORError)
def xor(a: SupportsBool, b: SupportsBool) -> bool:
    """Exclusive check for two values.

    Returns the scalar truthy value
    Raises XORError if both values are truthy or both values are falsy.
    """
    a = bool(a)
    b = bool(b)
    if a != b:
        return a or b
    msg = f"Only one value can be truthy, got a={a} and b={b}."
    raise XORError(msg)
