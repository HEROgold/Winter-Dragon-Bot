<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_errors` (wd-errors)
Errors for WinterDragon.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_errors` — `wd-errors/src/wd_errors/__init__.py`

- exports: BaseError, Refused, unwrap

## `wd_errors.base` — `wd-errors/src/wd_errors/base.py`
Base error class for Winter Dragon.

### `class BaseError(Exception)`
Base class for Winter Dragon's own errors.

## `wd_errors.extension` — `wd-errors/src/wd_errors/extension.py`
Module that contains extension related errors.

### `class ExtensionError(BaseError)`
Raised when an extension fails to load.

## `wd_errors.refused` — `wd-errors/src/wd_errors/refused.py`
Refusing an action: stop a command, button or listener and tell the user why.

- `unwrap[T](result: T | NetworkError, message: str) -> T` — Return ``result``, or refuse with ``message`` when it's a failed Discord call.

### `class Refused(BaseError)`
An action that can't go ahead; :attr:`message` tells the user who asked why.

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
