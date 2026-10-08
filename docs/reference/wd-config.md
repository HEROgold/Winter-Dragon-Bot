<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_config` (wd-config)
Module for a config descriptor.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_config` — `wd-config/src/wd_config/__init__.py`

- exports: Config, ConfigParser, DiscordConfig

## `wd_config.bot` — `wd-config/src/wd_config/bot.py`
Application wide bot settings.

- module names: GENERATED_MSG

### `class Settings`
Application wide Settings.

- attributes: log_level, bot_name, support_guild_id, prefix, application_id, bot_invite, auto_reload_extensions,
  auto_reload_poll_seconds, created_color, changed_color, deleted_color, bot_status_messages, PROTOCOL_PREFIX,
  SERVER_IP, WEBSITE_PORT, WEBSITE_URL, steam_redirect, TIME_FORMAT, DATE_FORMAT, DATETIME_FORMAT, OAUTH_SCOPE,
  BOT_SCOPE

## `wd_config.config` — `wd-config/src/wd_config/config.py`

### `class Config[T](CKConfig[T])`
Config descriptor for WinterDragon.

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
Endpoints for the discord API.

- attributes: base, version
- `@property api_version -> str` — Get the API version as a string.

## `wd_config.errors` — `wd-config/src/wd_config/errors.py`

### `class ConfigError(Exception)`
Base class for all configuration-related exceptions.

### `class FirstTimeLaunchError(ConfigError)`
Raised when it's detected that WinterDragon is launched for the first time.

## `wd_config.parser` — `wd-config/src/wd_config/parser.py`

### `class ConfigParser(configparser.ConfigParser)`
Custom config parser that handles the config file.

- `is_valid() -> bool` — Check if the config is valid.
- `get_invalid() -> Generator[str]` — Get all invalid config values.

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
