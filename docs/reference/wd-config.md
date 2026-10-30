<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_config` (wd-config)
Module for a config descriptor.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_config` — `wd-config/src/wd_config/__init__.py`

- exports: Config, DiscordConfig, OperatorFiles

## `wd_config.config` — `wd-config/src/wd_config/config.py`
The WinterDragon `Config` descriptor and how each scope binds its own ini file.

### `class OptionalFileWatcher(FileWatcher)`
A `FileWatcher` that treats a missing file as unchanged instead of failing to `stat` it.

- `has_changed() -> bool`

### `class Config[T](CKConfig[T])`
Config descriptor for WinterDragon.

- `@classmethod bind(file: Path, *, operator: bool=False, optional: bool=False) -> None` — Give this scope its own ``file``, so no other scope's parser overwrites it.
- `on_file_change(origin: Literal['get', 'set'], old: T, new: T) -> None` — Re-read this scope's file, so a value edited on disk is used from its next read on, without a restart.

## `wd_config.constants` — `wd-config/src/wd_config/constants.py`
Every config scope's ini file, declared once.

- module names: APP_CONFIG_FILE, COGS_CONFIG_FILE, BOT_CONFIG_FILE, DATABASE_CONFIG_FILE, DASHBOARD_CONFIG_FILE,
  ARCHIVE_CONFIG_FILE, DISCORD_CONFIG_FILE, SENTRY_CONFIG_FILE

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

## `wd_config.migration` — `wd-config/src/wd_config/migration.py`
The one-off migration of an old ini file whose sections now belong to other scopes.

- `migrate(legacy: Path, moves: Iterable[Move]) -> MigrationReport | None` — Migrate ``legacy`` by ``moves``; ``None`` when it holds nothing to move or drop (or doesn't exist).

### `@dataclass class Move`
Where the keys of one legacy section go.

- fields: section: str, file: Path, to_section: str | None, keys: Mapping[str, str] | None, drop: Collection[str],
  convert: Mapping[str, Callable[[str], str | None]], defaults: Mapping[str, str] | None
- `@property target_section -> str` — The section the keys land in.
- `target_key(key: str) -> str | None` — Return the target key ``key`` moves to, or ``None`` when this move doesn't take it.

### `@dataclass class MigrationReport`
What one migration did; every entry names a section or ``section.key``.

- fields: backup: Path, moved: tuple[str, ...], dropped: tuple[str, ...], defaulted: tuple[str, ...], kept: tuple[str,
  ...]

## `wd_config.parser` — `wd-config/src/wd_config/parser.py`
The first-launch check: operator-facing ini files must have every required value filled in.

- module names: REQUIRED
- `required(hint: str) -> str` — Return a :data:`REQUIRED` default followed by ``hint``, such as the URL the operator finds the value at.
- `is_required(value: str) -> bool` — Whether ``value`` is still a :data:`REQUIRED` default, with or without a hint.

### `class OperatorFiles`
The ini files an operator edits; each scope with operator settings registers its file here.

- `@classmethod register(file: Path) -> None` — Check ``file`` on first launch; a scope calls this once, next to its ``set_file``.
- `@classmethod unset() -> Generator[str]` — Yield ``file:section:key`` for every value still at the :data:`REQUIRED` default.
- `@classmethod check() -> None` — Raise :class:`FirstTimeLaunchError` listing every required value the operator hasn't filled in.

## `wd_config.sentry` — `wd-config/src/wd_config/sentry.py`
Configurable Sentry settings, backed by their own sentry.ini file.

### `class SentryConfig[T](Config[T])`
Config descriptor scoped to the Sentry settings file.

### `class Environments(enum.StrEnum)`
Enum for different environments.

- attributes: development, production, staging, test

### `class SentrySettings`
Configurable Sentry settings.

- attributes: Telemetry, dsn, environment
- `@classmethod resolved_dsn() -> str | None` — Return the DSN to pass to ``sentry_sdk.init``: ``None`` while it's empty or still :data:`REQUIRED`.
