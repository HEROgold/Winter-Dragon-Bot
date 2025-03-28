"""Utility functions for the bot."""
from collections.abc import Sequence
from types import UnionType
from typing import Any


type _ClassInfo = type | UnionType | tuple[_ClassInfo, ...]

def get_arg[T: _ClassInfo](args: Sequence[Any], target: T) -> T | None:
    """Get the first argument in a sequence that is an instance of the target class."""
    return next(
        (
            arg
            for arg in args
            if isinstance(
                arg,
                target,
            )
        ),
        None,
    )
