from collections.abc import Sequence
from types import UnionType
from typing import Any


type _ClassInfo = type | UnionType | tuple[_ClassInfo, ...]

def get_arg[T: _ClassInfo](args: Sequence[Any], target: T) -> T | None:
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
