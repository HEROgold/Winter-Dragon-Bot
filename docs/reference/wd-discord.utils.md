<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord.utils` (wd-discord)
Module for utility functions and classes.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord.utils` — `wd-discord/src/wd_discord/utils/__init__.py`

- exports: XORError, xor

## `wd_discord.utils.xor` — `wd-discord/src/wd_discord/utils/xor.py`
Generic utilities for the wd-discord package.

- `@with_known_exception xor(a: SupportsBool, b: SupportsBool) -> bool` — Exclusive check for two values.

### `class XORError(ValueError)`
Raised when both values are truthy or both values are falsy in an xor operation.
