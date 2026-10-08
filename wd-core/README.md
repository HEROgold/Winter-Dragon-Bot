# wd-core

Shared domain helpers above the transport: audit-log events (`AuditEvent`, `AuditEventFactory`, `AuditEventHandler`), gateway `Intents`, the Sentry setup, an httpxyz `AsyncClient` for third-party APIs, and `PackageVersion`.

- **Depends on:** wd-config, wd-discord (plus sentry-sdk).
- **Start here:** `wd_core.events` for audit logging, `wd_core.intents.Intents`, `wd_core.sentry.Sentry`.
- **API reference:** [wd_core](../docs/reference/wd-core.md) · [command](../docs/reference/wd-core.command.md) · [ui](../docs/reference/wd-core.ui.md)
