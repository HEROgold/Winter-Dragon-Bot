<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord.errors` (wd-discord)
Location of all discord and package related erros go.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord.errors` — `wd-discord/src/wd_discord/errors/__init__.py`

- exports: ApiErrorTree, ApiResponseError

## `wd_discord.errors.api` — `wd-discord/src/wd_discord/errors/api.py`
Error models for Discord API responses.

### `class ApiErrorTree(RootModel[ErrorNode | dict[str, 'ApiErrorTree']])`
Represents the entire error tree, which can be a single node or a dictionary of child nodes.

- fields: root: ErrorNode | dict[str, ApiErrorTree]

### `class ApiResponseError(BaseModel)`
The final model that can parse all three variants.

- fields: code: int, message: str, errors: ApiErrorTree | None
