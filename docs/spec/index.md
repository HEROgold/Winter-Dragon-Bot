# Winter Dragon specification

What the v2 bot and its web dashboard should do. The pages describe behaviour, not code: the code, the [API reference](../reference/index.md) and each command's own description hold the arguments and messages. Terms in **bold** are defined in the [glossary](../../GLOSSARY.md).

Winter Dragon is a **public** Discord bot: anyone may add it to their server, so every feature assumes many guilds, strangers as members, and a privacy promise it has to keep.

## Pages

- [Bot core](bot-core.md): command placement per guild, operator commands, announcements to guilds, errors.
- [User tools](user-tools.md): reminders, fuel log, Steam sales, Urban Dictionary, invites, uptime.
- [Server management](server-management.md): automatic voice channels, roles on join and rejoin, welcome messages, stats channels, server announcements.
- [Moderation](moderation.md): log channels, the server log, infractions, ban networks, purge, channel utilities.
- [Games](games.md): tournaments, game registry and looking for group, hangman, question games, love meter, League of Legends, Clash.
- [Ranked tracking](ranked-tracking.md): holding Tracked Players accountable for their Climb.
- [Data and privacy](data-and-privacy.md): how data is stored, deleted, restored and purged; command usage.
- [Web dashboard](dashboard.md): its pages, sign-in, who may see what.
- [Archive](archive.md): a separate read-only bot that records every gateway event into the database.

## Words

- **Guild** in this spec, the glossary and the code; **server** in everything a user reads (bot replies, command descriptions, the dashboard). Users never see "guild".
- The people: **member**, **guild admin** (Discord's Manage Server permission), **bot owner**, **tournament organiser**.

## How a feature is described

Each feature lists, where it applies: its purpose; **who** uses it; its **commands** (names only); what it **stores**; its **rules and limits**; its **settings** (`cogs.ini` sections, edited by the bot owner); what the **dashboard** shows; and its **status**:

| Status | Meaning |
|---|---|
| **Live** | Built in `src/winter_dragon/cogs/`. |
| **Port** | Exists on `main` (and as a copy in `wd-cogs`); to be rebuilt in `src/winter_dragon/cogs/` as specified here. |
| **New** | Has no implementation anywhere yet. |

Developer examples (`heartbeat`, `message_logger`) and dropped `main` features are not part of the bot; dropped ones are listed at the end of their area page so nobody ports them by accident.

## Decisions behind this spec

- [ADR 0002](../adr/0002-htmx-jinja-dashboard.md): the dashboard is htmx 4 and Jinja templates served by the FastAPI service.
- [ADR 0003](../adr/0003-herogold-models-and-soft-delete.md): bot tables are herogold models with soft delete by default.
- [ADR 0004](../adr/0004-alembic-migrations-applied-on-start.md): schema changes are Alembic revisions, applied by a one-shot service before the bot starts.
- [ADR 0005](../adr/0005-archive-stores-gateway-events-naively.md): the archive stores gateway events naively, as current-state entities and append-only history without foreign keys.
