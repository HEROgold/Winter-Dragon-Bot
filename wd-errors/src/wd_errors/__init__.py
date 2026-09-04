"""Errors for WinterDragon."""

from __future__ import annotations

lazy from .base import Activity, BaseError, ErrorCode, ErrorMessage, ErrorNode, Platform


__all__ = [
    "Activity",
    "BaseError",
    "ErrorCode",
    "ErrorMessage",
    "ErrorNode",
    "Platform",
]

_ = ""  # < Trick for ruff. so that imports below don't get auto-sorted.
# Eagerly import all error handlers.
# These register themselves with the ErrorFactory using __init_subclass__.
# from .handlers import *
# TODO: ^^^^ Is temporarily commented out, as it depends on discord.py, which we're going to fully replace
# using wd-discord. Once we have wd-discord fully implemented, we can re-enable this import.
