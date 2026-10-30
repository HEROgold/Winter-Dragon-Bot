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

- attributes: bot_name, support_guild_id, dashboard_url, log_level, created_color, changed_color, deleted_color,
  bot_status_messages

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
- `capture_model_warnings() -> None` — Send ``wd_discord.models``' log records (unknown-field warnings) through this gateway's handlers.

## `winter_dragon.health` — `src/winter_dragon/health.py`
Container health checks, run by compose: ``python -m winter_dragon.health bot`` or ``... web``.

- module names: ALIVE_FILE, ALIVE_MAX_AGE, WEB_TIMEOUT, CHECKS
- `bot_healthy() -> bool` — Return whether :data:`ALIVE_FILE` was touched within :data:`ALIVE_MAX_AGE` seconds.
- `web_healthy() -> bool` — Return whether the dashboard's landing page answers 200 on this host.
- `main(argv: list[str]) -> int` — Run the check named by ``argv[0]`` and return the exit code.

## `winter_dragon.redirect_link` — `src/winter_dragon/redirect_link.py`
Links to the dashboard's ``/redirect`` page, which opens an app link (``steam://...``) Discord won't make clickable.

- module names: REDIRECT_PATH, BLOCKED_SCHEMES, FALLBACK_SCHEME

### `class UnsafeLinkError(ValueError)`
A link the redirect page won't open; the message says why, for the visitor who followed it.

### `@dataclass class RedirectLink`
Where the redirect page sends a visitor: ``uri``, ``mobile`` on a phone, and a ``fallback`` page without the app.

- fields: uri: str, mobile: str | None, fallback: str | None
- `target(*, phone: bool) -> str` — Return the link to open: :attr:`mobile` on a phone when there is one, else :attr:`uri`.
- `on(dashboard_url: str) -> str` — Return the URL of this link's redirect page on the dashboard served at ``dashboard_url``.

## `winter_dragon.run_test_bot` — `src/winter_dragon/run_test_bot.py`
Run a real wd_bot.Bot for up to 10 minutes against the live Discord API.

- module names: RUN_DURATION_SECONDS
- `async main() -> int` — Run the bot for up to RUN_DURATION_SECONDS, then report the outcome.
