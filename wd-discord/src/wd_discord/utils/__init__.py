""""Module for utility functions and classes."""
from __future__ import annotations

lazy from .strings import LimitedString
lazy from .xor import XORError, xor


__all__ = ["LimitedString", "XORError", "xor"]
