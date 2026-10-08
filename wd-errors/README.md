# wd-errors

Shared error machinery: `BaseError` and error codes (`wd_errors.base`), the self-registering `ErrorFactory`, size errors (`TooShortError`, `TooLongError`, `BoundsError`), `ExtensionError` and `StartupError`.

- **Depends on:** wd-discord (`Embed`, the gateway `Interaction` model) — imported but not declared in `pyproject.toml` (known debt).
- **Registration:** subclassing `DiscordError` registers the handler with `ErrorFactory` at import time, so the package `__init__` must import every handler module.
- **Legacy:** `wd_errors.handlers` wraps discord.py exception types (`CommandInvokeError`, `CommandNotFound`).
- **API reference:** [wd_errors](../docs/reference/wd-errors.md) · [handlers](../docs/reference/wd-errors.handlers.md)
