---
name: discord-api-models
description: How wd-discord validates Discord API responses with pydantic v2 — the DiscordModel base, pydantic-aware value types (Snowflake/ImageHash), PermissionsField coercion, unknown-field Sentry telemetry, and where REST methods live (stores, partial and bound entities, errors as values). Use when adding or parsing any Discord REST/gateway response type, adding a field to Application/Guild/Channel/User, or adding a REST operation to a store or entity.
---

# Discord API models (wd-discord)

Every object parsed from a Discord REST or gateway **response** is a validated pydantic v2
model. Outbound (object→API) bodies follow the rule in [architecture](../architecture/SKILL.md).

## The base: `DiscordModel`

All response models subclass `DiscordModel` ([models.py](../../../wd-discord/src/wd_discord/models.py)), never `BaseModel` directly:

```python
class DiscordModel(BaseModel):
    model_config = ConfigDict(
        extra="allow",           # keep unknown keys in model_extra so we can report them
        populate_by_name=True, validate_by_name=True, validate_by_alias=True,
        frozen=False,
    )
```

`extra="allow"` (not `ignore`/`forbid`): a transport layer must survive Discord shipping new
keys, but must not silently drop them. A `model_validator(mode="after")` on the base sends any
`model_extra` to Sentry via `_report_unknown_fields`, gated by `SentrySettings.Telemetry`
([wd-config](../../../wd-config/src/wd_config/sentry.py)). The reporter is best-effort — wrapped
in `try/except` so telemetry never turns a successful parse into a failure. `sentry_sdk.capture_message`
is a no-op until `sentry_sdk.init` runs, so this is safe outside the bot runtime. Reading the
Config flag is layering-clean (wd-discord already depends on wd-config); `sentry-sdk` is a direct
wd-discord dependency.

## Value types are pydantic-aware, never bare primitives

IDs are `Snowflake`, image hashes are `ImageHash` — never `int`/`str`. Both carry a
`__get_pydantic_core_schema__` hook so pydantic validates/coerces the wire value into the rich
type and serialises it back ([snowflake.py](../../../wd-discord/src/wd_discord/snowflake.py),
[image.py](../../../wd-discord/src/wd_discord/image.py)):

```python
@classmethod
def __get_pydantic_core_schema__(cls, source, handler) -> CoreSchema:
    return core_schema.no_info_plain_validator_function(
        cls._validate,  # int|str -> Snowflake ; str -> ImageHash ; else TypeError
        serialization=core_schema.plain_serializer_function_ser_schema(
            lambda s: str(s._snowflake), return_schema=core_schema.str_schema(), when_used="json"),
    )
```

Discord sends IDs as **decimal strings**, so `Snowflake` serialises back to `str` for
`model_dump(mode="json")`. See also [value-modeling](../value-modeling/SKILL.md).

## `PermissionsField` for bitfields

Discord serialises permission bitfields as decimal **strings**, but `Permissions` is an
`IntFlag`. Use the shared alias on every permission field — never a bare `Permissions`:

```python
# permissions.py
type PermissionsField = Annotated[Permissions, BeforeValidator(lambda value: Permissions(int(value)))]
```

Reused on `PermissionOverwrite.allow/deny`, `Role.permissions`, `Guild.permissions`,
`InstallParams.permissions`.

## Where REST methods live: stores and entities, errors are values

`Client` is transport only (`request`/`get`/`post`/..., rate limits, gateway bootstrap). Resource
operations live in [entities/](../../../wd-discord/src/wd_discord/entities/), in three shapes per resource:

- a **Store** creates, fetches and lists (`client.users`, `client.channels`, `client.guilds`,
  `client.application.commands`). `EntityStore(client, PartialX)` gives `partial(id)` and `fetch(id)` for
  free; subclass it only for extra operations (`UserStore.me`, `GlobalCommandStore.create`). Stores nest
  where Discord's routes do: application commands hang off `client.application`, guild commands will hang
  off a guild;
- a **`Partial*`** entity acts knowing only an ID, without fetching (`client.users.partial(id).send(...)`).
  It is just `class PartialUser(BaseUser, Partial[User])`: `Partial` supplies `client` and `id`, and the
  `Base*` mixin (listed first, so its `fetch` wins) supplies the actions;
- a full **entity** wraps the fetched data model (`entity.model`), defines `id` from it, and inherits the
  same `Base*` actions.

Every method returns `T | NetworkError` and never raises on API/network failure; consumers import
`is_network_error`/`NetworkError` from `wd_discord`. Everything holding a client inherits `ClientBound`
from [entities/base.py](../../../wd-discord/src/wd_discord/entities/base.py), whose `_entity` /
`_entities` helpers do the check-validate-wrap step (`parse` and `no_content` cover model-only and
empty responses):

```python
async def fetch(self) -> User | NetworkError:
    """GET /users/{user_id}."""
    return self._entity(await self.client.get(t"/users/{self.id}"), UserModel, User)
```

Routes are t-strings, never f-strings: [route.py](../../../wd-discord/src/wd_discord/route.py) `Route`
percent-encodes each parameter into the path and builds the rate-limit key from the template, keeping only
the major parameter (`guilds`/`channels`/`webhooks` id) and collapsing every other one to `{id}`. Join
route pieces with `+` (`self._webhook_path + t"/messages/@original"`).

Entity classes take the plain names (`wd_discord.User`); data models keep the Discord docs' names in
their modules and are imported as `... as UserModel` where both meet.

Gateway dispatches follow the same split: `wd_discord.gateway.events` parses each dispatch into a data
model, and `wd_discord.bind(client, model)` ([entities/events.py](../../../wd-discord/src/wd_discord/entities/events.py))
wraps it in its entity (`Message`, `Guild`, `Ready`, a typed `Interaction` subclass, ...) so listeners act
without passing a client around; events with no entity yet come back as `RawEvent`. `event_entities()`
is the event → entity map that generates `wd_bot/listener.pyi`. Interactions bind to
`CommandInteraction`/`ComponentInteraction`/`AutocompleteInteraction` with `respond`/`defer`/
`edit_original`/`followup` (plus `update`/`defer_update` on components).

Find a store's or entity's methods in [docs/reference/wd-discord.entities.md](../../../docs/reference/wd-discord.entities.md)
and data-model fields in [docs/reference/wd-discord.resources.md](../../../docs/reference/wd-discord.resources.md)
before opening source.

Test code built on wd-discord with `wd_discord.testing.RecordingClient`: it records each request and
answers from canned `reply(...)`/`fail(...)` values, so stores and entities run unchanged offline.

## Gotchas

- **Concrete imports for nested models.** A field typed as another `DiscordModel` must be imported
  at runtime (not under `TYPE_CHECKING`) so pydantic can resolve the annotation. Ruff's `TC001`
  is silenced repo-wide for pydantic bases via `runtime-evaluated-base-classes` in `ruff.toml`.
- **One-way subpackage deps.** `application` imports `guild`; `guild`/`channel` never import
  `application`. Keep it acyclic — a concrete cross-subpackage import is fine only in that direction.
- **`Annotated` metadata is comma-form.** `User` fields carry `Annotated[T, OAuthScopes.X]`;
  `validate_scopes` reads `model_fields[name].metadata`. Use commas for multiple scopes
  (`Annotated[T, OAuthScopes.IDENTIFY, OAuthScopes.PREMIUM]`), never `A | B` — `OAuthScopes.__or__`
  returns a plain `str` that the `isinstance(m, OAuthScopes)` filter misses.
- **Forward-compat enums.** Fields Discord expands often (e.g. `Guild.features`) stay `list[str]`,
  not `list[SomeEnum]`, so unknown future values don't fail validation.
- Adding a dependency (e.g. sentry-sdk) goes through `uv add`, never a hand-edit — see
  [dependencies](../dependencies/SKILL.md).
