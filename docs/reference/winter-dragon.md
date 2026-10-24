<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon` (winter-dragon)
Winter Dragon: the Discord bot and its web dashboard.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.config` — `src/winter_dragon/config.py`
The app's own config scopes: app-wide settings in ``config.ini``, cog settings in ``cogs.ini``.

- module names: CONFIG_FILE, COGS_CONFIG_FILE

### `class Config[T](BaseConfig[T])`
Config descriptor scoped to the app-wide settings file.

### `class CogConfig[T](BaseConfig[T])`
Config descriptor scoped to the cog settings file; every cog shares it, one section per settings class.

### `class Settings`
Application-wide settings.

- attributes: bot_name, support_guild_id, log_level, created_color, changed_color, deleted_color, bot_status_messages

## `winter_dragon.config_migration` — `src/winter_dragon/config_migration.py`
Where every section of the old single ``config.ini`` lives now, and the startup step that moves it there.

- module names: CONFIG_INI, COGS_INI, BOT_INI, DATABASE_INI, SENTRY_INI, DISCORD_INI, MOVES
- `migrate_legacy_config() -> MigrationReport | None` — Move the old single ``config.ini`` into the per-scope files, logging what moved and what was dropped.

## `winter_dragon.event_logger` — `src/winter_dragon/event_logger.py`
A bot that does nothing but log every frame the Discord gateway sends it.

- `async main() -> None` — Connect with every intent and log events until interrupted.

### `class EventLoggingGateway(Gateway)`
A gateway that logs every frame it receives as raw JSON before handling it.

- `async log_ready(name: str, event: DiscordModel) -> None` — Log READY, which :meth:`connect` consumes before :meth:`_handle` sees it; other events are logged raw.

## `winter_dragon.run_test_bot` — `src/winter_dragon/run_test_bot.py`
Run a real wd_bot.Bot for up to 10 minutes against the live Discord API.

- module names: RUN_DURATION_SECONDS
- `async main() -> int` — Run the bot for up to RUN_DURATION_SECONDS, then report the outcome.
