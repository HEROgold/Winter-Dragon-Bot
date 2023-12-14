from typing import Any, Sequence


def get_arg(args: Sequence[Any], target: type) -> Any | None:
    for arg in args:
        if isinstance(arg, target):
            return arg
