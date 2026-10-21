# Archive

A separate, read-only bot that records everything Discord's gateway sends it into the database, so later features (statistics, a server Wrapped, activity and voice sessions) can be built on the data. It is not part of the public bot: it runs under its own token, and the public bot's promise in [Data and privacy](data-and-privacy.md) doesn't cover it. The technical decisions are in [ADR 0005](../adr/0005-archive-stores-gateway-events-naively.md).

- **Who:** the bot owner runs it next to (or without) the public bot. Nobody interacts with it.
- **Commands:** none. It never syncs commands or calls Discord's REST API; it only reads gateway events.
- **Status:** New.

## What it listens to

- Every guild its application is in, from the moment it joins, with every intent (privileged ones included; they must be enabled in the developer portal).
- Every frame Discord sends is also written to the log file, as the event logger does.

## What it stores

Data is stored naively: as Discord sent it, without judging whether a feature needs it.

### Raw events

Every received event, unchanged: its name, guild, sequence number, when it arrived and its payload. Kept **30 days**, then purged by the archive's own daily task. This is what lets the other tables be rebuilt after a model gains fields, and what the reports read.

### Entities

The current state of each Discord object the events carry: guilds, channels and threads, roles, users, members, emojis, stickers, messages, and the rest as they get modelled.

- One row per object, overwritten by each newer copy. A guild sent again on every connect simply overwrites what is already there.
- A copy only overwrites the fields it contains: an event carrying part of an object never erases the rest.
- A delete event marks the object deleted; it is kept. An object that is created again is restored.
- Fields Discord sends that the models don't know yet are kept with the object as extra data, replaced by each newer copy.
- Lists inside an object (a message's attachments, embeds and components, a member's roles, a channel's permission overwrites, …) are stored as rows of their own, in order, replaced whenever a newer copy includes that list. A nested object that can only appear once is stored with its parent.

### History

Events that are about something happening rather than an object's state are appended and never changed:

- presence updates (status, devices, and each activity: games, listening, streaming, custom status);
- voice state changes;
- typing;
- reactions added and removed;
- message edits: the content and edit time of each version.

When the archive connects, each guild's current presences and voice states are appended too, marked as a snapshot, so history has a starting point after every downtime.

Activity sessions (how long someone played a game) and voice sessions (how long someone was in a channel) are **not** stored: they are computed from this history when a feature needs them.

### Events without a model

An event that wd-discord has no model for is kept only as a raw event (30 days). Every event is meant to get its own model and table over time.

## Rules and limits

- Receiving events never waits on the database: rows are queued and written in batches.
- If the database is unreachable the queue holds up to a limit; beyond it the newest rows are dropped, the number dropped is logged and reported, and the log file still has them.
- Objects refer to each other by Discord ID only. A message may refer to a user or channel the archive has never seen; that is not an error.
- The archive applies database migrations itself when it starts, so it runs with or without the public bot.

## Reports

- **Changing fields:** from the raw events, which fields of which objects change most often. This decides later which objects should keep their history instead of only their current state.
- **Unmodelled events:** which event names arrived without a model, and which fields the models don't know yet.

## Settings

- `bot.ini` `[Tokens]` `read_only_token`: the archive's token. When empty, it uses `discord_token`.
- `archive.ini`: the intents, the batch size and interval, the queue limit, and how many days raw events are kept.

## Not yet

- Keeping the history of objects (versions) instead of only their current state; waits for the changing-fields report.
- Privacy handling: opting out, deleting a member's or guild's archived data.
- Storing activity and voice sessions instead of computing them.
- A model and table for every gateway event.
