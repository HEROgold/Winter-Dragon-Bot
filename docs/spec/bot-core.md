# Bot core

The behaviour every feature relies on. The runtime itself (extension loading, hot reload, command sync, permissions, errors, telemetry, configuration) lives in the `wd-*` packages and is described in their READMEs; this page covers what guilds and the bot owner see of it.

## Command placement per guild

A guild admin chooses which of the bot's commands their guild has, so a server that only wants tournaments doesn't get thirty other commands.

- **Who:** guild admins.
- **Rules:**
  - A guild is in **whitelist** mode (only the listed commands) or **blacklist** mode (all but the listed ones); entries are top-level commands or whole groups.
  - The command-management commands themselves can never be removed from a guild.
  - Changing the policy re-places that guild's commands and syncs them to Discord at once. A command any guild filters can't stay global, so it becomes guild-scoped for each guild that allows it.
- **Stores:** one policy per guild, with its entries.
- **Dashboard:** a section of server settings: mode, and a checklist of commands and groups.
- **Status:** New. Designed in GH #206; the command registry already has the `Placement` hook and `refresh()`.

## Command sync

The bot keeps Discord's registered commands in step with what its cogs declare, without hitting Discord's sync rate limit needlessly.

- **Who:** bot owner.
- **Commands:** `/bot-commands list` (each command's synced or pending state), `/bot-commands resync`.
- **Dashboard:** the owner panel shows the same list and a resync button.
- **Status:** Live, [bot_commands.py](../../src/winter_dragon/cogs/bot_commands.py).

## Operator commands

What the bot owner runs from Discord itself.

- **Who:** bot owner.
- **Commands:** set the bot's presence (`/activity` on `main`); latency (`/ping`); resource use and its graph (`/performance` on `main`).
- **Settings:** `Settings.bot_status_messages` in `config.ini`, the presences the bot rotates through.
- **Dashboard:** the owner panel shows latency, resource use, command sync, and command usage (see [Data and privacy](data-and-privacy.md#command-usage)).
- **Status:** Port, redesigned around the owner panel. `main`'s passive "data tracking" cog, which copied messages, presence and the rest of Discord into the database, is **dropped**; only command usage is kept.

## Announcements to guilds

The bot owner tells every guild about the bot: new features, downtime.

- **Who:** bot owner sends; guild admins choose whether and where they receive them.
- **Commands:** `/announce` (bot owner).
- **Rules:** an announcement goes only to guilds whose guild admin picked a **bot updates channel**; guilds without one receive nothing. Nothing is ever posted to a guild's system channel unasked.
- **Stores:** each guild's bot updates channel.
- **Dashboard:** the bot updates channel is picked in server settings; the owner panel has the announcement form.
- **Status:** Port, redesigned (on `main` it broadcast to every guild).

## Error reporting

When a command can't run, the member is told what is missing (a permission, a role, a channel overwrite) in plain words, never a stack trace; unexpected errors go to Sentry.

- **Status:** Live, in `wd-bot` and `wd-errors`.
