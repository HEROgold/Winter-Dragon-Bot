<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_errors.handlers` (wd-errors)

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_errors.handlers` — `wd-errors/src/wd_errors/handlers/__init__.py`

- exports: AppCommandInvokeError, CommandNotFoundError

## `wd_errors.handlers.base` — `wd-errors/src/wd_errors/handlers/base.py`
Base error handler class for app command errors.

### `class BaseError(DiscordError, ABC, error_type=BaseError)`
Base error handler class for app command errors.

- fields: title: str, description: str, footer: str
- `@property timestamp_str -> str` — Returns the timestamp of when the error occurred in HH:MM:SS.mmm format.
- `create_embed() -> Embed`

## `wd_errors.handlers.command_invoke_error` — `wd-errors/src/wd_errors/handlers/command_invoke_error.py`
Handler for CommandInvokeError - catches unhandled exceptions in commands.

### `class AppCommandInvokeError(BaseError, error_type=CommandInvokeError)`
Handler for CommandInvokeError - catches all unhandled exceptions in app commands.

- attributes: error_title, error_description

## `wd_errors.handlers.not_found` — `wd-errors/src/wd_errors/handlers/not_found.py`
Handler for CommandNotFound - catches unhandled exceptions in commands.

### `class CommandNotFoundError(BaseError, error_type=CommandNotFound)`
Handler for CommandNotFound - catches all unhandled exceptions in app commands.

- attributes: error_title, error_description
