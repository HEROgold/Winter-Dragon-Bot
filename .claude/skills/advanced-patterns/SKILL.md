---
name: advanced-patterns
description: When to write a descriptor and when to define a Protocol in WinterDragonV2. Use when adding validated/computed attributes, typing an untyped third-party library, avoiding an import of a concrete discord.py/httpxyz type, using cast, or designing structural interfaces.
---

# Descriptors & Protocols

## Descriptors — reusable attribute behavior

Reach for a descriptor when the same get/set policy applies to many attributes: validation, persistence, computed access. Two in-tree families:

**Validating field:** `LimitedString` ([wd_discord/utils/strings.py](../../../wd-discord/src/wd_discord/utils/strings.py)) subclasses herogold's `DataDescriptor[str, object]`; `__set__` raises on over-length input, `__get__` is wrapped with `@with_known_exception(AttributeError)` so unset access returns the error as a value. Used as a dataclass field default: `name: str = LimitedString(32)` ([interactions.py](../../../wd-discord/src/wd_discord/interactions.py)). Write a descriptor like this instead of repeating `if len(x) > N: raise` in `__post_init__` bodies.

**Persistent setting:** the whole config system — `Config[T]` descriptors persist to ini files (see the config-and-constants skill). Note the class-level state gotcha: descriptor classes can hold shared parser state that subclass scopes must reset ([wd_config/discord.py:13-21](../../../wd-config/src/wd_config/discord.py#L13)).

Conventions when writing one:

- Base on `herogold.protocols.DataDescriptor[Value, Owner]` rather than raw `__get__`/`__set__` when it fits.
- Failures follow the errors-as-values contract where practical.
- Keep the descriptor generic and dumb; the limit/policy is the constructor argument.

## Protocols — structural contracts instead of concrete imports

Define a `Protocol` when you need a *shape*, not a class. Three sanctioned uses in this repo:

1. **Decouple from a heavy library.** `Mentionable` ([wd-types/src/wd_types/protocol.py](../../../wd-types/src/wd_types/protocol.py), `@runtime_checkable`) lets [wd-core/events.py](../../../wd-core/src/wd_core/events.py) do `isinstance(target, Mentionable)` over discord.py entities without importing their classes. Cross-package protocols live in **wd-types**.

2. **Type an untyped third-party API.** The `Cassiopeia*` protocols in [wd-cogs/src/wd_cogs/games/league_of_legends.py](../../../wd-cogs/src/wd_cogs/games/league_of_legends.py) describe just the attributes actually used. This beats `cast`/`Any`: pyright checks your usage against the protocol. (Caveat: those protocols are currently duplicated in `lol_clash.py` — if you touch them, consolidate to one module and import.)

3. **Capability branching at runtime.** `Prunable`/`History`/`PrunableHistory` ([wd-cogs/src/wd_cogs/server/purge.py](../../../wd-cogs/src/wd_cogs/server/purge.py)) are `@runtime_checkable` and composed by inheritance (`class PrunableHistory(Prunable, History, Protocol)`), so code branches on what a channel *can do*. Same composition style in the URL specs of [wd-discord/src/wd_discord/endpoints.py](../../../wd-discord/src/wd_discord/endpoints.py) (`UrlSpecWithUserInfo(URLSpec, UserInfoHelpers, Protocol)`), which model endpoint URLs structurally instead of committing to a concrete URL class.

Conventions:

- Add `@runtime_checkable` **only** if the protocol is used with `isinstance`; leave it off for purely static contracts.
- Keep protocols minimal — only the members callers use.
- Compose protocols by inheriting several plus `Protocol` again, rather than making one fat interface.

## Decision ladder for "the type doesn't fit"

1. Can you declare a `Protocol` for what you actually use? → do that.
2. Is it a one-off narrowing of a dynamic object you don't control? → `cast("Type", obj)` (string-literal form), sparingly.
3. Truly untypable? → `Any` with `# noqa: ANN401` at that site.

Never blanket-ignore; see the code-style skill.
