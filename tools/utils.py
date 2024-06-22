from collections.abc import Sequence
from typing import Any


def get_arg[T](args: Sequence[Any], target: T) -> T | None:
    return next(
        (
            arg
            for arg in args
            if isinstance(
                arg,
                target,  # type: ignore
            )
        ),
        None,
    )
