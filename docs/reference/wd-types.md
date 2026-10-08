<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_types` (wd-types)

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_types.alias` — `wd-types/src/wd_types/alias.py`
Contains type aliases for WinterDragon.

- `type Store[T] = dict[str, T]`
- `type CoroutineFunction[Args = Any, Yield = Any, Send = Any, Return = Any] = Callable[[Args], Coroutine[Yield, Send, Return]]`
- `type MaybeAwaitable[T] = T | Awaitable[T]`
- `type MaybeAwaitableFunc[**P, T] = Callable[P, MaybeAwaitable[T]]`

## `wd_types.protocol` — `wd-types/src/wd_types/protocol.py`
Contains protocols for WinterDragon.

### `@runtime_checkable class Mentionable(Protocol)`
A protocol for objects that can be mentioned in Discord.

- `@property mention -> str` — Return the string that can be used to mention this object.
