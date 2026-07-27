# Bot Core

The runtime the rest of the bot is built on: how extensions get discovered and loaded, how the slash-command tree stays in sync with Discord, how configuration and errors are handled, and the operator-facing commands for driving the bot from inside Discord.

Audience: maintainers and the bot developer. Most of this is invisible to ordinary server members.

---

## Extension discovery and loading

Extensions are found by walking the extensions package rather than being listed by hand. Each cog declares whether it should load automatically (`auto_load=True`); anything prefixed with `_` is skipped. Cogs that need setup work expose a load hook the bot calls after construction, so an extension can be a plain class with no boilerplate `setup()` function.

**Status:** ✅ Ported — `wd-bot/src/wd_bot/bot.py`, `cogs.py`, `extension_manager.py`.
**Source on `main`:** `src/winter_dragon/bot/core/bot.py`, `core/cogs.py`, `core/extension_manager.py`, `extensions/__init__.py`

## Hot reload

A filesystem watcher reloads changed extensions while the bot is running, so development does not require a restart. The watcher tracks its own state (idle/watching/reloading) to avoid reloading mid-reload.

**Status:** ✅ Ported — `wd-bot/src/wd_bot/auto_reload.py`.
**Source on `main`:** `src/winter_dragon/bot/core/auto_reload.py`

## Command tree synchronisation

Syncing the application command tree with Discord is rate-limited, so the bot avoids doing it needlessly. It records a signature for every synced command definition and only pushes a sync when a signature actually changed. Alongside the automatic path there is a manual sync surface (`/sync`, plus a developer-only variant that syncs every guild) for when a sync must be forced.

A cache of application commands — global and per guild — backs command lookups, so cogs can resolve a command's Discord-side ID (for mention-style command links) without re-fetching.

**Status:** ✅ Ported for the runtime pieces (`wd-bot/src/wd_bot/auto_sync.py`, `cache.py`); 🟡 for the `/sync` cog, which still imports `winter_dragon.bot.ui`.
**Source on `main`:** `src/winter_dragon/bot/core/auto_sync.py`, `core/app_command_cache.py`, `extensions/bot_extension/sync.py`

## Per-guild command enable/disable

Server admins can turn individual commands off for their guild through an interactive, paginated toggle UI (`/manage-commands`). Disabled commands are recorded per guild and refused at invocation time — the command still exists in Discord's tree, it just declines to run.

**Status:** 🟡 Copied, unwired — depends on the missing UI toolkit and command/guild tables.
**Source on `main`:** `src/winter_dragon/bot/extensions/bot_extension/command_manager.py`

## Permission handling

When a command cannot run because the bot or the invoking user lacks something, the bot reports *what* is missing — permissions, roles, or channel overwrites — rather than failing opaquely.

**Status:** ✅ Ported — `wd-bot/src/wd_bot/permissions.py`.
**Source on `main`:** `src/winter_dragon/bot/core/permissions.py`

## Error handling

Command errors are routed through a registry: each handler class declares the exception type it handles and is registered automatically, and a factory resolves an incoming exception to its handler. Unhandled exceptions inside commands and command-not-found both have dedicated handlers, so users get a sensible reply instead of a silent failure.

**Status:** ✅ Ported — the `wd-errors` package.
**Source on `main`:** `src/winter_dragon/bot/errors/`

## Configuration

Settings are declared as typed descriptors on the classes that use them, backed by `config.ini` and `discord.ini`. Values can be composed — a setting can be assembled from other settings plus literal fragments (for example building a URL out of a host and a port), so derived values stay derived instead of being duplicated.

**Status:** ✅ Ported — the `wd-config` package.
**Source on `main`:** `src/winter_dragon/bot/core/settings.py`, `src/winter_dragon/config/`

## Scheduled tasks

A wrapper around Discord's task loops adds logging and error reporting, so a background loop that throws is surfaced rather than dying quietly. Used throughout the bot for polling, cleanup, and periodic refreshes.

**Status:** ✅ Ported — `wd-bot/src/wd_bot/tasks.py`, `routines.py`.
**Source on `main`:** `src/winter_dragon/bot/core/tasks.py`

## Telemetry

Sentry integration is environment-aware (development vs production) and captures unhandled errors from both the event loop and command execution.

**Status:** ✅ Ported — `wd-core/src/wd_core/sentry.py`, `wd-config/src/wd_config/sentry.py`.
**Source on `main`:** `src/winter_dragon/bot/core/sentry.py`

---

## Operator commands

Bot-developer and admin surfaces for running the bot from Discord itself.

- **Bot control** (`/botcontrol …`) — cross-server announcements from the bot owner.
- **Bot activity** (`/activity`) — change the bot's presence/status.
- **Metrics** (`/ping`, `/performance`, `/performance_graph`) — latency, resource usage, and a rendered performance graph. Developer-only for the latter two.
- **Data tracking** — a passive cog that mirrors users, guilds, roles, channels, messages, presence, and command usage into the database, and registers a generic listener for every Discord audit-log action.

**Status:** 🟡 Copied, unwired for all four — every one depends on the missing table models.
**Source on `main`:** `src/winter_dragon/bot/extensions/bot_extension/`
