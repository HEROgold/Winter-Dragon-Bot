# archive

A separate, read-only bot that records every gateway event into the database, to stress test wd-discord and the database on an existing server ([spec](../../docs/spec/archive.md), [ADR 0005](../../docs/adr/0005-archive-stores-gateway-events-naively.md)).

- **Run:** `uv run python -m archive [--database-url URL]`; reports: `uv run python -m archive.reports {changing-fields,unmodelled}`.
- **Depends on:** wd-discord (gateway, event models), wd-db (lifecycle models, custom data), wd-bot (`Tokens`), winter_dragon (`EventLoggingGateway`, migrations).
- **Start here:** `handlers.py` says what each event writes; `mapping.py` how a payload maps onto a table (columns by Discord field name, `<field>_<subfield>` for nested objects, `children` for lists, the rest as custom data); `models/` holds the tables.
- **Adding a field:** add a column named after the Discord field to its table, then generate a migration; the field moves out of the custom data on its own.
- **Adding an event:** give it a model in `wd_discord.gateway.events`, then a handler in `HANDLERS` (a test fails until every modelled event has one).
