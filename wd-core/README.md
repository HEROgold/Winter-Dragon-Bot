# wd-core

Shared domain helpers above the transport: the bot's default intents and permissions, the Sentry setup, and `PackageVersion`. Transport types (`Intents`, request payloads) live in wd-discord.

- **Depends on:** wd-config, wd-discord, wd-types (plus sentry-sdk).
- **Start here:** `wd_core.sentry.Sentry`, `wd_core.constants`.
- **API reference:** [wd_core](../docs/reference/wd-core.md)
