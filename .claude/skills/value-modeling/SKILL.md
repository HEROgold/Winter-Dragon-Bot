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

See [authenticate.py](../../../wd-discord/src/wd_discord/authenticate.py): `Token`, `UserAgentVersion`, `URL`, `MetaData`. Signatures then demand the right one — `get_auth_header(type_: TokenType, token: Token)` won't take a random string. Follow this pattern for any new token/URL/identifier-ish string.

## Structured scalars: small dataclasses

When a primitive has internal structure, wrap it and expose the parts as properties. The canonical example is [snowflake.py](../../../wd-discord/src/wd_discord/snowflake.py): `Snowflake` wraps one `int` and decodes `timestamp`, `worker_id`, `process_id`, `increment` via bit operations. All Discord IDs are `Snowflake`, never `int` (see the `ApplicationCommand` fields in [interactions.py](../../../wd-discord/src/wd_discord/interactions.py)).

When such a value type is used as a **field on a pydantic model** (any `DiscordModel`), give it a `__get_pydantic_core_schema__` classmethod so pydantic validates/coerces the wire value into the rich type and serialises it back — `Snowflake` (from `int|str`, back to a decimal `str`) and `ImageHash` (from `str`) both do this. That keeps API data validated without exposing bare primitives on the model. See the [discord-api-models](../discord-api-models/SKILL.md) skill for the recipe and the `PermissionsField`/`Annotated`-metadata patterns.

## Choosing the Enum flavor

| Flavor | Use when | Repo example |
|---|---|---|
| `StrEnum` | the value is sent/compared as a string (wire values, mime types, routing keys); use `auto()` when the lowercase name IS the value | `ContentType`, `TokenType` ([authenticate.py](../../../wd-discord/src/wd_discord/authenticate.py)), `Buckets` ([rate_limit.py:25](../../../wd-discord/src/wd_discord/rate_limit.py#L25)), `OAuthScopes` ([oauth.py](../../../wd-discord/src/wd_discord/oauth.py)) |
| `IntEnum` | an external protocol defines numeric codes — write the explicit numbers | `Opcode` ([gateway/connection.py:35](../../../wd-discord/src/wd_discord/gateway/connection.py#L35)), `ChannelType` ([permissions.py:16](../../../wd-discord/src/wd_discord/permissions.py#L16)) |
| `IntFlag` | independent booleans that combine — one flag field instead of N bool attributes | `CogFlags` ([wd-bot/src/wd_bot/cogs.py:36](../../../wd-bot/src/wd_bot/cogs.py#L36)), `WatcherFlags` ([auto_reload.py:22](../../../wd-bot/src/wd_bot/auto_reload.py#L22)), `Permissions` ([permissions.py:58](../../../wd-discord/src/wd_discord/permissions.py#L58)) |
| plain `Enum` | pure states/identities with no meaningful value | `Tags` ([wd-db/src/wd_db/channel_types.py](../../../wd-db/src/wd_db/channel_types.py)), `MatchStatus`/`Events` driving a state machine ([wd-cogs/src/wd_cogs/tournament/status.py](../../../wd-cogs/src/wd_cogs/tournament/status.py)) |

IntFlag conventions used here:

- Members via `auto()`; combined defaults as a module value: `default_flags = CogFlags(CogFlags.AutoLoad | CogFlags.AutoReload)`.
- Wrap bit tests in readable properties: `is_enabled` returns `bool(self & WatcherFlags.Enabled)` ([auto_reload.py:31](../../../wd-bot/src/wd_bot/auto_reload.py#L31)) — callers never do raw `&` checks.
- "Private" flags are underscore-prefixed (`_HasAppCommandMentions`).

Two richer patterns worth reusing:

- **Enum-of-dataclass**: when each member carries data, make the member value a frozen dataclass — `Locales` in [interactions.py:34](../../../wd-discord/src/wd_discord/interactions.py#L34) stores full `Locale` records.
- **Annotated members**: `Permissions` members carry `Annotated[...]` metadata naming which `ChannelType`s they apply to, validated via `__metadata__` ([permissions.py](../../../wd-discord/src/wd_discord/permissions.py)). Attach constraints to the type, not to scattered runtime checks.

## Typed dict-shaped data

- Kwargs contracts: `TypedDict` + `Required`/`NotRequired` + `Unpack` — `BotArgs` ([wd-bot/src/wd_bot/cogs.py:29](../../../wd-bot/src/wd_bot/cogs.py#L29)).
- Constrained fields: use validating descriptors like `LimitedString(32)` ([wd_discord/utils/strings.py](../../../wd-discord/src/wd_discord/utils/strings.py)) instead of manual length checks; the `@validate` decorator in [interactions.py](../../../wd-discord/src/wd_discord/interactions.py) runs `Annotated` validators (`required_if`, `absent_if`) from `__post_init__`.

## Anti-patterns (real, in-tree)

- Duplicated enums: `Region`/`Platform` exist in both `riot_clash_api.py` and `league_of_legends.py`, plus a stray `league_of_legends.py.tmp`. Don't copy an enum into a second module — import it from one owner.
