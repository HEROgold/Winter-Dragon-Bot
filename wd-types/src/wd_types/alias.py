"""Contains type aliases for WinterDragon."""
from __future__ import annotations

lazy from collections.abc import Awaitable, Callable, Coroutine, Iterable
lazy from typing import Any


type Store[T] = dict[str, T]

type CoroutineFunction[Args = Any, Yield = Any, Send = Any, Return = Any] = Callable[[Args], Coroutine[Yield, Send, Return]]

type MaybeAwaitable[T] = T | Awaitable[T]
type MaybeAwaitableFunc[**P, T] = Callable[P, MaybeAwaitable[T]]

type _Prefix = Iterable[str] | str
