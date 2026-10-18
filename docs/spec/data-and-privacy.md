# Data and privacy

What the bot stores, and how it keeps its promises about it. Because the bot is public, a member must be able to see and delete everything it stores about them.

## Storage

Every table is a herogold model ([ADR 0003](../adr/0003-herogold-models-and-soft-delete.md)):

- By default a `BaseModel`: deleting a record only marks it deleted, and a deleted record is not present anywhere: not in commands, not on the dashboard, not in counts.
- A `DataModel` where the history itself is read: infractions and guild-setting changes.
- A row that is one per Discord object uses that object's Discord ID as its `id`; a row keyed by several IDs gets its own `id` and a unique key.
- Creating a record whose key exists but is deleted restores it.

The bot stores only what a feature needs. It does not copy messages, presence or the rest of Discord into its database; live Discord state comes from wd-discord's cache.

## Who data belongs to

- **Member data:** what a member stores for themselves, in any guild: reminders, refuels, Steam alerts, their voice-channel name and limit, linked accounts, tournament sign-ups, Notes, command usage. Roles kept for them on rejoin are also listed, as they are about the member.
- **Guild data:** what a guild admin set up, and what lives inside one guild: hubs, stats channels, log channels, welcome, roles on join, command placement, ban networks, infraction settings, tournaments, the tracking channel.

## A member deletes their data

- **Who:** any member, from Your data on the dashboard.
- **Rules:**
  - The member is told exactly what they will lose, and confirms by typing their username.
  - All their member data is deleted at once (hidden everywhere) and **purged permanently 30 days later**. It can't be undone.
  - Tournaments that haven't started lose them; a team they captain is disbanded.
  - Each step is recorded so Your data shows the request's progress.
- **Status:** New.

## A guild removes the bot

- **Rules:**
  - When the bot is removed, the guild becomes a **departed guild**: all its guild data is deleted (hidden).
  - If the bot is re-added within **30 days**, everything is restored as it was.
  - After 30 days the guild data is purged permanently.
  - Member data is untouched: it belongs to the members.
- **Status:** New.

## Purging

A cog owns a daily asyncio task that purges member data 30 days after a deletion request and departed guilds 30 days after they left, and listens for the bot being removed from and re-added to guilds. It can move to the worker service once that exists, without changing this behaviour.

- **Status:** New.

## Command usage

The bot counts, per day, how often each member used each command in each guild.

- **Stores:** one count per member, command, guild and day.
- **Who reads it:** the bot owner sees totals and per-member figures on the owner panel; a member sees their own usage on Your data; a guild admin sees per-command totals for their guild, without names.
- **Rules:** counts are member data, so they are deleted with the member; and any count older than **12 months** is purged.
- **Status:** New.
