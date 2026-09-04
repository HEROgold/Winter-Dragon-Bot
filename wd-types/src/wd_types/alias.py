"""Contains type aliases for WinterDragon."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine, Iterable, Mapping
from typing import Any


type Store[T] = dict[str, T]

type CoroutineFunction[Args = Any, Yield = Any, Send = Any, Return = Any] = Callable[[Args], Coroutine[Yield, Send, Return]]

type MaybeAwaitable[T] = T | Awaitable[T]
type MaybeAwaitableFunc[**P, T] = Callable[P, MaybeAwaitable[T]]

type _Prefix = Iterable[str] | str
type _PrefixCallable[BotT: BotBase] = MaybeAwaitableFunc[[BotT, Message], _Prefix]
type PrefixType[BotT: BotBase] = _Prefix | _PrefixCallable[BotT]

type Bot[T: BotBase] = T

type MentionableTargetType = (
    AppCommand
    | GuildChannel
    | Member
    | Role
    | Thread
    | User
)

type CommandStore = Store[AppCommand | AppCommandGroup]
type PermissionsOverwrites = Mapping[Role | Member | Object, PermissionOverwrite]
type ResponseTypes = Embed | str
