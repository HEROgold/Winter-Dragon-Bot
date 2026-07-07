---
name: discord-api-models
description: How wd-discord validates Discord API responses with pydantic v2 — the DiscordModel base, pydantic-aware value types (Snowflake/ImageHash), PermissionsField coercion, unknown-field Sentry telemetry, and the errors-as-values getter pattern. Use when adding or parsing any Discord REST/gateway response type, adding a field to Application/Guild/Channel/User, or wiring a new Client resource method.
---

# Discord API models (wd-discord)

Every object parsed from a Discord REST or gateway **response** is a validated pydantic v2
model. Outbound (object→API) builders stay plain — see [architecture](../architecture/SKILL.md).

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

## Getter pattern: errors are values

`Client` resource methods return `Model | ApiResponseError | RequestError` — they never raise on
API/network failure ([client.py](../../../wd-discord/src/wd_discord/client.py)):

```python
async def get_user(self, user_id: int | str) -> User | ApiResponseError | RequestError:
    result = await self.get(f"/users/{user_id}")
    if isinstance(result, ApiResponseError | RequestError):
        return result
    return User.model_validate(result.json())
```

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
