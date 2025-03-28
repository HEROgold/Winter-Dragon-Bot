"""Module contains a function that returns a select query with an id attribute."""

from collections.abc import Callable, Sequence
from typing import overload

from sqlmodel import SQLModel


class WithID[T = SQLModel](T): # type: ignore[reportUntypedBaseClass]
    """A class that inherits from another class and adds an id attribute."""

    id: int


@overload
def with_id[T](entity: Sequence[T]) -> Sequence[T]: ...

@overload
def with_id[T](entity: T) -> T: ...

def with_id[T](entity: T | Sequence[T]) -> T | Sequence[T]:
    """Mark an entity as having an id attribute."""
    return entity


def with_id_wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
    """Add an id attribute to the result of a function."""
    def inner(*args: P.args, **kwargs: P.kwargs) -> F:
        result = func(*args, **kwargs)
        return with_id(result)
    return inner
