<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_config` (wd-config)
Module for a config descriptor.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_config` — `wd-config/src/wd_config/__init__.py`

- exports: Config, DiscordConfig, OperatorFiles

## `wd_config.bot` — `wd-config/src/wd_config/bot.py`
Application wide bot settings.

- module names: GENERATED_MSG

### `class Settings`
Application wide Settings.

- attributes: log_level, bot_name, support_guild_id, prefix, bot_invite, created_color, changed_color, deleted_color,
  bot_status_messages, PROTOCOL_PREFIX, SERVER_IP, WEBSITE_PORT, WEBSITE_URL, steam_redirect, TIME_FORMAT, DATE_FORMAT,
  DATETIME_FORMAT, OAUTH_SCOPE

## `wd_config.config` — `wd-config/src/wd_config/config.py`
The WinterDragon `Config` descriptor and how each scope binds its own ini file.

### `class OptionalFileWatcher(FileWatcher)`
A `FileWatcher` that treats a missing file as unchanged instead of failing to `stat` it.

- `has_changed() -> bool`

### `class Config[T](CKConfig[T])`
Config descriptor for WinterDragon.

- `@classmethod bind(file: Path, *, operator: bool=False, optional: bool=False) -> None` — Give this scope its own ``file``, so no other scope's parser overwrites it.

## `wd_config.constants` — `wd-config/src/wd_config/constants.py`

- module names: CONFIG_FILE, DISCORD_CONFIG_FILE

## `wd_config.data_types` — `wd-config/src/wd_config/data_types.py`
Custom confkit data types shared across settings.

### `class Combined(BaseDataType[str])`
A data type that combines multiple Config descriptors and literals.

- `convert(value: str) -> str` — Convert from a string to the combined data type.

## `wd_config.db` — `wd-config/src/wd_config/db.py`
Configurable database connection settings.

### `class DbUrl`
Class containing database URL components.

- attributes: driver_name, database, username, password, host, port

## `wd_config.discord` — `wd-config/src/wd_config/discord.py`
Discord-scoped configuration, backed by its own discord.ini file.

### `class DiscordConfig[T](Config[T])`
Config descriptor scoped to the discord settings file.

### `@dataclass class URLS`
Every Discord host the library talks to or links to, and the API version they speak.

- attributes: base, version, gateway, cdn, web, invite
- `@property api_version -> str` — Get the API version as a string.
- `@property gateway_query -> str` — The `?v=...&encoding=json` query appended to a gateway URL (https://docs.discord.com/developers/topics/gateway#connecting).
- `@property gateway_url -> str` — The default gateway URL: the configured gateway host with the version and encoding query.
- `@property oauth2_authorize -> str` — The OAuth2 authorization URL bot invites are built on (https://docs.discord.com/developers/topics/oauth2#authorization-url).

### `class RestCache`
How long a REST read asked to be cached is reused before it's sent again.

- attributes: ttl

### `class RateLimit`
How the REST client handles Discord's 429 responses.

- attributes: max_retries

### `class UserAgent`
The `User-Agent` header the REST client sends, in Discord's `DiscordBot (url, version)` form.

- attributes: url, version

## `wd_config.errors` — `wd-config/src/wd_config/errors.py`

### `class ConfigError(Exception)`
Base class for all configuration-related exceptions.

### `class FirstTimeLaunchError(ConfigError)`
Raised when it's detected that WinterDragon is launched for the first time.

## `wd_config.parser` — `wd-config/src/wd_config/parser.py`
The first-launch check: operator-facing ini files must have every required value filled in.

- module names: REQUIRED

### `class OperatorFiles`
The ini files an operator edits; each scope with operator settings registers its file here.

- `@classmethod register(file: Path) -> None` — Check ``file`` on first launch; a scope calls this once, next to its ``set_file``.
- `@classmethod unset() -> Generator[str]` — Yield ``file:section:key`` for every value still at the :data:`REQUIRED` default.
- `@classmethod check() -> None` — Raise :class:`FirstTimeLaunchError` listing every required value the operator hasn't filled in.

## `wd_config.reminder` — `wd-config/src/wd_config/reminder.py`
Settings for personal reminders.

### `class ReminderSettings`
How often due reminders are looked for.

- attributes: check_interval

## `wd_config.sentry` — `wd-config/src/wd_config/sentry.py`
Configurable Sentry settings.

### `class Environments(enum.StrEnum)`
Enum for different environments.

- attributes: development, production, staging, test

### `class SentrySettings`
Configurable Sentry settings.

- attributes: Telemetry, dsn, environment

## `wd_config.stats` — `wd-config/src/wd_config/stats.py`
Settings for the guild stats channels.

### `class StatsSettings`
How often the stats channels are renamed to show the current counts.

- attributes: update_interval

## `wd_config.steam` — `wd-config/src/wd_config/steam.py`
Settings for the Steam sale finder.

### `class SteamSettings`
How often Steam is scraped, and how its sales are shown.

- attributes: country_code, stored_percent, complete_percent, top_sellers, request_interval, update_interval,
  outdated_after, recheck_delay, embed_color

## `wd_config.urban` — `wd-config/src/wd_config/urban.py`
Settings for the Urban Dictionary lookup.

### `class UrbanSettings`
Which Urban Dictionary lookups are allowed, and how much of a result is shown.

- attributes: allow_random, max_definitions
