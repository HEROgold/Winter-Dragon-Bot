<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_errors` (wd-errors)
Errors for WinterDragon.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_errors` — `wd-errors/src/wd_errors/__init__.py`

- exports: Activity, BaseError, ErrorCode, ErrorMessage, ErrorNode, Platform

## `wd_errors.base` — `wd-errors/src/wd_errors/base.py`
Base error classes for the wd-discord package.

### `class ErrorCode(StrEnum)`
Various error codes that can be returned by the Discord API.

- attributes: BASE_TYPE_CHOICES, BASE_TYPE_REQUIRED, APPLICATION_COMMAND_TOO_LARGE

### `class Platform(StrEnum)`
Platform a user is using to access Discord.

- attributes: DESKTOP, ANDROID, IOS

### `class Activity(IntEnum)`
Activity a user is engaged in on Discord.

- attributes: PLAYING, STREAMING, LISTENING, WATCHING, CUSTOM, COMPETING

### `class ErrorMessage(BaseModel)`
Error message with a code and a message string.

- fields: code: ErrorCode, message: str

### `class BaseError(Exception)`
Base class for all errors in the wd-discord package.

### `class ErrorNode(BaseModel)`
Node in the error tree, which can contain a list of error messages and/or child nodes.

- fields: errors_list: list[ErrorMessage]

## `wd_errors.error` — `wd-errors/src/wd_errors/error.py`
Base error helpers for Discord command handling.

### `class DiscordError(ABC, LoggerMixin)`
Base class for Error.

- `async handle() -> None` — Handle the Error.
- `create_embed() -> Embed` — Create an embed for the Error.
- `async send_message(response: Embed | str) -> None` — Send an embed response to the interaction or context.

## `wd_errors.extension` — `wd-errors/src/wd_errors/extension.py`
Module that contains extension related errors.

### `class ExtensionError(BaseError)`
Raised when an extension fails to load.

## `wd_errors.factory` — `wd-errors/src/wd_errors/factory.py`
Module for creating Error errors lazy from Error log entries.

### `class ErrorFactory`
Factory for creating Error errors.

- fields: registry: ClassVar[dict[type[DiscordException], list[type[DiscordError]]]], logger: ClassVar
- `@classmethod register(error: type[DiscordException], error_type: type[DiscordError]) -> None` — Register an Error error class for a category.
- `@classmethod get_handlers(bot: BotBase, exception: DiscordException, *, interaction: Interaction | None=None, ctx: Context[Bot] | None=None) -> Generator[DiscordError]` — Get the Error error class for a category.

## `wd_errors.size` — `wd-errors/src/wd_errors/size.py`
Size errors.

### `class SizeError(ValueError)`
Raised when a value is the wrong size.

### `class InexactSizeError(SizeError)`
Raised when a string is not the expected length.

### `class TooShortError(SizeError)`
Raised when a string is shorter than the minimum length.

### `class TooLongError(SizeError)`
Raised when a string exceeds the maximum length.

### `class BoundsError(SizeError, ExceptionGroup)`
Raised when a value is out of bounds.

## `wd_errors.startup` — `wd-errors/src/wd_errors/startup.py`
Startup errors for the bot.

### `class StartupError(BaseError, RuntimeError)`
Raised when the bot fails to start up properly.
