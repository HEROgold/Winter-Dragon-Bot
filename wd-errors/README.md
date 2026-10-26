# wd-errors

Shared error machinery: `Refused` and `unwrap` (errors as values), `BaseError` and error codes (`wd_errors.base`), size errors (`TooShortError`, `TooLongError`, `BoundsError`), `ExtensionError` and `StartupError`.

- **Depends on:** nothing in the workspace; wd-discord and wd-bot depend on it.
- **Unhandled exceptions** aren't handled here: wd-bot logs them (Sentry picks the log up) and replies with `wd_bot.guard.error_embed`, which names the interaction ID the log line carries.
- **API reference:** [wd_errors](../docs/reference/wd-errors.md)
