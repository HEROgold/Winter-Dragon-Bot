---
name: value-modeling
description: How WinterDragonV2 avoids primitive obsession and when to use each Enum flavor. Use when adding domain values, IDs, tokens, flags, statuses, choosing between StrEnum/IntEnum/IntFlag/Enum, or when tempted to pass a bare str/int through an API.
---

# Value modeling — no naked primitives

A bare `str` or `int` crossing a function boundary is a design smell here. Give the value a type.

## Distinct string types: subclass `str`

This repo does **not** use `NewType`. Nominal string types are empty `str` subclasses:

```python
class Token(str):
    """Discord bot token."""

    __slots__ = ()
```

See [authenticate.py](../../../wd-discord/src/wd_discord/authenticate.py): `Token`, `UserAgentVersion`, `URL`, `MetaData`. Signatures then demand the right one — `get_auth_header(type_: TokenType, token: Token)` won't take a random string. `SteamURL` in [winter_dragon/cogs/steam/urls.py](../../../src/winter_dragon/cogs/steam/urls.py) is the same move in app code. Follow this pattern for any new token/URL/identifier-ish string.

## Structured scalars: small dataclasses

When a primitive has internal structure, wrap it and expose the parts as properties. The canonical example is [snowflake.py](../../../wd-discord/src/wd_discord/snowflake.py): `Snowflake` wraps one `int` and decodes `timestamp`, `worker_id`, `process_id`, `increment` via bit operations. All Discord IDs are `Snowflake`, never `int` (see the `ApplicationCommand` fields in [interactions.py](../../../wd-discord/src/wd_discord/interactions.py)). When the kind is part of the identity, the dataclass carries both: `StoreItemID(kind, id)` in [steam/urls.py](../../../src/winter_dragon/cogs/steam/urls.py) — Steam app, package and bundle IDs are separate ranges.

When such a value type is used as a **field on a pydantic model** (any `DiscordModel`), give it a `__get_pydantic_core_schema__` classmethod so pydantic validates/coerces the wire value into the rich type and serialises it back — `Snowflake` (from `int|str`, back to a decimal `str`) and `ImageHash` (from `str`) both do this. That keeps API data validated without exposing bare primitives on the model. See the [discord-api-models](../discord-api-models/SKILL.md) skill for the recipe and the `PermissionsField`/`Annotated`-metadata patterns.

## Choosing the Enum flavor

| Flavor | Use when | Repo example |
|---|---|---|
| `StrEnum` | the value is sent/compared as a string (wire values, mime types, routing keys); use `auto()` when the lowercase name IS the value | `ContentType`, `TokenType` ([authenticate.py](../../../wd-discord/src/wd_discord/authenticate.py)), `Buckets` ([rate_limit.py](../../../wd-discord/src/wd_discord/rate_limit.py)), `Locale` ([interactions.py](../../../wd-discord/src/wd_discord/interactions.py)), `OAuthScopes` ([oauth.py](../../../wd-discord/src/wd_discord/oauth.py)) |
| `IntEnum` | an external protocol defines numeric codes — write the explicit numbers | `Opcode` ([gateway/connection.py](../../../wd-discord/src/wd_discord/gateway/connection.py)), `ChannelType` ([permissions.py](../../../wd-discord/src/wd_discord/permissions.py)), `InteractionType` ([gateway/events.py](../../../wd-discord/src/wd_discord/gateway/events.py)) |
| `IntFlag` | independent booleans that combine — one flag field instead of N bool attributes | `CogFlags` ([wd_bot/cogs.py](../../../wd-bot/src/wd_bot/cogs.py)), `WatcherFlags` ([auto_reload.py](../../../wd-bot/src/wd_bot/auto_reload.py)), `Permissions` ([permissions.py](../../../wd-discord/src/wd_discord/permissions.py)) |
| plain `Enum` | pure states/identities with no meaningful value | `Tags` ([wd_db/channel_types.py](../../../wd-db/src/wd_db/channel_types.py)), `ScrapeFailure` as an error value ([steam/scrapers.py](../../../src/winter_dragon/cogs/steam/scrapers.py)), `MatchStatus`/`Events` state machine ([wd_cogs/tournament/status.py](../../../wd-cogs/src/wd_cogs/tournament/status.py)) |

IntFlag conventions used here:

- Members via `auto()`; combined defaults as a module value: `default_flags = CogFlags.AutoLoad | CogFlags.AutoReload`.
- Wrap bit tests in readable properties: `is_enabled` returns `bool(self & WatcherFlags.Enabled)` (`WatcherFlags.is_enabled` in [auto_reload.py](../../../wd-bot/src/wd_bot/auto_reload.py)) — callers never do raw `&` checks.

A richer pattern worth reusing:

- **Annotated members**: `Permissions` members carry `Annotated[...]` metadata naming which `ChannelType`s they apply to, checked by `Permissions.validate_channel` via `__metadata__` ([permissions.py](../../../wd-discord/src/wd_discord/permissions.py)). Attach constraints to the type, not to scattered runtime checks.

## Typed dict-shaped data

- Kwargs contracts: `TypedDict` + `Required`/`NotRequired` + `Unpack` — `BotArgs` ([wd_bot/cogs.py](../../../wd-bot/src/wd_bot/cogs.py)).
- Constrained strings/lists: pydantic `Annotated` constraints as reusable aliases — `type Name = Annotated[str, StringConstraints(min_length=1, max_length=32)]`, `Field(max_length=MAX_CHOICES)` in [interactions.py](../../../wd-discord/src/wd_discord/interactions.py) — not manual length checks.

## Anti-patterns (real, in-tree)

- Duplicated enums: `Region`/`Platform` exist in both `riot_clash_api.py` and `league_of_legends.py`, plus a stray `league_of_legends.py.tmp`. Don't copy an enum into a second module — import it from one owner.
