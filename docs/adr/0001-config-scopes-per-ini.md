# One confkit Config subclass and ini file per scope

`wd-config` holds only the configuration of the `wd-*` library packages; the app in `src/winter_dragon` declares its own `Config` subclass (and a `CogConfig` for cog settings) on top of it. Each scope binds its own ini file — `config.ini` and `cogs.ini` for the app, `bot.ini`, `database.ini`, `sentry.ini` and `discord.ini` for the libraries — because two confkit `Config` classes bound to the same file each get their own parser, and whichever writes last drops the sections the other added.

## Considered Options

- **One ini file per cog.** Rejected: every file needs its own `Config` subclass and parser, so 20+ cogs means 20+ of each. Cogs share `cogs.ini`, one section per cog.
- **Splitting `bot.ini` into operator and internal files.** Rejected: one more file for the operator to learn. A required operator setting is marked by its `"!!"` default instead.
- **An `expose_internal_config` flag.** Rejected in favour of the file's own existence: an internal-only file that doesn't exist is never written and its in-code defaults apply; creating the file (even empty) exposes it, and confkit fills in the defaults on the next start; deleting it resets to the defaults.

## Consequences

- Operator-facing files (`config.ini`, `cogs.ini`, `bot.ini`, `database.ini`, `sentry.ini`) are written on first launch with `"!!"` for required values and checked by `FirstTimeLaunchError`.
- `discord.ini` is internal-only, so it exists only for developers who created it. `bot.ini` keeps wd-bot's internal settings next to the operator ones, so those are always written.
- The one-off migration from the old single `config.ini` (backed up to `config.ini.bak`) moves known sections to their new files, drops unknown ones, and creates an internal file only when it carries a value changed from its default — which exposes that scope.
- A new scope must call `set_file` and reset `_parser` / `_has_read_config` after subclassing, as `DiscordConfig` does, or it silently shares its parent's file.
