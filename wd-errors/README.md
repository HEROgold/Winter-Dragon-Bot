# wd-errors

Shared error machinery: `Refused` and `unwrap` (errors as values), `BaseError` (`wd_errors.base`), size errors (`TooShortError`, `TooLongError`, `BoundsError`), `ExtensionError` and `StartupError`.

- **Depends on:** wd-discord, at runtime only: `unwrap` and `Refused` (`wd_errors.refused`) lazily import `NetworkError` and `is_network_error` from it. The pyproject doesn't declare it, because wd-discord depends on wd-errors; installing wd-errors alone works until `unwrap` runs. The rest of the package imports nothing from the workspace. wd-discord and wd-bot depend on it.
- **Discord API types** (the field-error tree `ErrorNode`/`ErrorMessage`/`ErrorCode`, `ActivityType`) live in wd-discord, not here.
- **Unhandled exceptions** aren't handled here: wd-bot logs them (Sentry picks the log up) and replies with `wd_bot.guard.error_embed`, which names the interaction ID the log line carries.
- **API reference:** [wd_errors](../docs/reference/wd-errors.md)
