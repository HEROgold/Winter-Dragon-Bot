<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord.errors` (wd-discord)
Location of all discord and package related erros go.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord.errors` — `wd-discord/src/wd_discord/errors/__init__.py`

- exports: ApiErrorTree, ApiResponseError, JsonErrorCode

## `wd_discord.errors.api` — `wd-discord/src/wd_discord/errors/api.py`
Error models for Discord API responses.

- module names: UNKNOWN_RANGE

### `class JsonErrorCode(IntEnum)`
Codes Discord puts in a failed response's ``code`` (https://docs.discord.com/developers/topics/opcodes-and-status-codes#json).

- attributes: GENERAL_ERROR, UNKNOWN_CHANNEL, UNKNOWN_GUILD, UNKNOWN_MEMBER, UNKNOWN_MESSAGE, UNKNOWN_OVERWRITE,
  UNKNOWN_ROLE, UNKNOWN_USER, TARGET_NOT_IN_VOICE, MISSING_ACCESS, CANNOT_DM_USER, MISSING_PERMISSIONS

### `class ApiErrorTree(RootModel[ErrorNode | dict[str, 'ApiErrorTree']])`
Represents the entire error tree, which can be a single node or a dictionary of child nodes.

- fields: root: ErrorNode | dict[str, ApiErrorTree]

### `class ApiResponseError(BaseModel)`
The final model that can parse all three variants.

- fields: code: int, message: str, errors: ApiErrorTree | None, status: int
- `@property unknown_resource -> bool` — Whether the request named something that doesn't exist (any more): Discord's 10xxx "Unknown ..." codes.
