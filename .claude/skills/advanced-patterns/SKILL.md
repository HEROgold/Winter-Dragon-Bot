---
name: advanced-patterns
description: When to write a descriptor and when to define a Protocol in WinterDragonV2. Use when adding validated/computed attributes, typing an untyped third-party library, avoiding an import of a concrete discord.py/httpxyz type, using cast, or designing structural interfaces.
---

# Descriptors & Protocols

## Descriptors — reusable attribute behavior

Reach for a descriptor when the same get/set policy applies to many attributes. In-tree families:

**Persistent setting:** the whole config system — `Config[T]` descriptors persist to ini files (see the config-and-constants skill). Gotcha: descriptor classes can hold shared parser state that a subclass scope must reset — the `DiscordConfig` block in [wd_config/discord.py](../../../wd-config/src/wd_config/discord.py).

**Non-binding callable attributes:** `AppCommand.__get__` ([wd_bot/commands.py](../../../wd-bot/src/wd_bot/commands.py)) and `ComponentHandler.__get__` ([wd_bot/components.py](../../../wd-bot/src/wd_bot/components.py)) return `self`, so a decorated cog method stays the command/handler object instead of becoming a bound method. Copy this when a decorator replaces a method with a callable object.

**Validation is not a descriptor job any more.** Length/shape limits on outbound Discord bodies are pydantic `Annotated` constraints — `type Name = Annotated[str, StringConstraints(min_length=1, max_length=32)]` in [wd_discord/interactions.py](../../../wd-discord/src/wd_discord/interactions.py). Reuse those aliases; don't write `if len(x) > N: raise` or a validating descriptor.

Conventions when writing one:

- Base on `herogold.protocols.DataDescriptor[Value, Owner]` rather than raw `__get__`/`__set__` when it fits.
- Failures follow the errors-as-values contract where practical.
- Keep the descriptor generic and dumb; the limit/policy is the constructor argument.

## Protocols — structural contracts instead of concrete imports

Define a `Protocol` when you need a *shape*, not a class. Sanctioned uses:

1. **Decouple from a heavy library.** `Mentionable` ([wd_types/protocol.py](../../../wd-types/src/wd_types/protocol.py), `@runtime_checkable`) lets [wd_core/events.py](../../../wd-core/src/wd_core/events.py) do `isinstance(target, Mentionable)` without importing entity classes. Cross-package protocols live in **wd-types**.
2. **One shape, several concrete types.** `SyncedRow` / `CommandLike` ([wd_bot/auto_sync.py](../../../wd-bot/src/wd_bot/auto_sync.py)) let `SyncedCommands[Row: SyncedRow]` treat `GlobalSyncedCommand` and `GuildSyncedCommand` tables the same.
3. **Type an untyped third-party API.** The `Cassiopeia*` protocols in [wd_cogs/games/league_of_legends.py](../../../wd-cogs/src/wd_cogs/games/league_of_legends.py) describe only the attributes used. (Debt: duplicated in `lol_clash.py` — consolidate if you touch them.)
4. **Capability branching at runtime.** `Prunable`/`History`/`PrunableHistory` ([wd_cogs/server/purge.py](../../../wd-cogs/src/wd_cogs/server/purge.py)) are `@runtime_checkable` and composed by inheritance, so code branches on what a channel *can do*.

Conventions:

- `@runtime_checkable` **only** if the protocol is used with `isinstance`.
- Keep protocols minimal — only the members callers use.
- Compose by inheriting several protocols plus `Protocol` again, rather than one fat interface.

## Decision ladder for "the type doesn't fit"

1. Can you declare a `Protocol` for what you actually use? → do that.
2. Is it a one-off narrowing of a dynamic object you don't control? → `cast("Type", obj)` (string-literal form), sparingly.
3. Truly untypable? → `Any` with `# noqa: ANN401` at that site.

Never blanket-ignore; see the code-style skill.
