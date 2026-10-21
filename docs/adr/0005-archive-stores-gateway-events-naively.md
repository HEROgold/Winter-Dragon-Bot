# The archive stores gateway events naively: current-state entities, append-only history, no foreign keys

The [archive](../spec/archive.md) is its own package, `src/archive`, run as `python -m archive`. It is a bare `Gateway` subclass (extending the event logger's `EventLoggingGateway`), never `wd_bot.Bot`, so it has no REST client and can't sync commands. Its tables live in the bot's PostgreSQL database and Alembic history: `migrations/env.py` imports `archive.models` next to the cogs.

Every received frame is appended to a raw `gateway_event` table (JSONB payload), purged after 30 days. Entities are `DiscordKeyedModel` rows holding only their current state: each copy is upserted with just the fields its payload set (`model_fields_set`), `*_DELETE` events soft-delete, and a re-create restores. Entities without a single Discord ID (members, reactions) keep an auto-increment `id` with a unique key on their IDs. Events about something happening (presence, voice state, typing, reaction add/remove, message revisions) are append-only herogold `BaseModel` rows with `received_at`; the presences and voice states inside `GUILD_CREATE` are appended as snapshot rows. Every list inside a payload is a child table with a `position`, replaced wholesale when a newer payload includes the list; a one-off nested object becomes prefixed columns on its parent; components are one self-referencing table. Fields the models don't know are stored as herogold `CustomData`.

Tables refer to each other by plain indexed Discord ID columns, with no foreign keys and no `Relationship`. The gateway handler only turns events into rows and puts them on a bounded `asyncio.Queue`; one writer task owns the single `Session`, writes in batches, commits, `expunge_all()`s, and rolls back and retries on failure.

## Considered Options

- **Versioned entities (a row per change).** Rejected for now: nobody reads entity history yet, and the 30-day raw table can answer "what changed" while a report finds which fields change often enough to deserve versioning.
- **Foreign keys or `herogold.orm.Relationship` between archive tables.** Rejected: events arrive in any order, and some referenced objects are never sent (a deleted user's author ID), so enforced relations would fail inserts or force placeholder rows. The archive records what Discord said; it is not domain data. This is the one exception to linking models with `Relationship`.
- **Writing inside the gateway handler.** Rejected: a slow database or a large `GUILD_CREATE` would delay heartbeats and get the connection dropped.
- **Storing activity and voice sessions as they happen.** Rejected for now: they can be computed from the append-only history at any time, including after a model fix, and downtime would leave open sessions to repair.
- **A table per gateway event straight away.** Deferred: events without a wd-discord model stay in the raw table until modelled; a table per event is the goal.
- **A separate database or schema.** Rejected: the measured volume is tens of MB a month, and one migration history and backup routine is simpler.

## Consequences

- herogold's `CustomDataContainer.set()` saves through herogold's own session, raises FastAPI's `HTTPException` and sizes data with `getsizeof`; the archive links `CustomData` rows with its own session until HeroPy fixes it, and `include_object` stops excluding the archive models' custom-data tables.
- A full queue drops rows (logged and reported to Sentry); the log file is the fallback.
- The archive applies migrations on start, so it doesn't depend on the public bot having run them.
- [Data and privacy](../spec/data-and-privacy.md) describes the public bot; the archive is a separate application, and its own privacy handling is deferred.
