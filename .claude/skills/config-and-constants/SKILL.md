---
name: config-and-constants
description: Where configurable values, constants, and derived settings live in WinterDragonV2 (confkit Config descriptors, config.ini/cogs.ini/discord.ini/bot.ini/database.ini/sentry.ini, Settings classes). Use when adding a setting, a constant, an env-like value, a URL/port/token, or when unsure what the source of truth for a value is.
---

# Config, constants & source of truth

Configuration is the **confkit descriptor system** — not `os.environ`, not dotenv, not hardcoded literals. Every value has exactly one owner; everything else imports or derives from it.

## The decision

- **Can an operator ever want to change it?** → a descriptor of the scope that owns it: the app's `Config`/`CogConfig`, or the owning `wd-*` package's scope.
- **Is it fixed by a protocol/spec?** (Discord epoch, header names, SQL keywords) → a module constant in the owning package's `constants.py`.
- **Is it computed from other settings?** → a property or function reading them, never a second literal.

## Configurable values: one `Config[T]` scope per ini file

[wd_config/config.py](../../../wd-config/src/wd_config/config.py) defines the base `class Config[T](CKConfig[T])` and `Config.bind(file, *, operator=False, optional=False)`. **The base `Config` is bound to no file**: every settings class belongs to a scope, a `Config` subclass bound to its own ini file. A descriptor declared on the bare base fails loudly (confkit: "Config file is not set"). Two scopes must never share a file — each gets its own parser and the last write drops the other's sections ([ADR 0001](../../../docs/adr/0001-config-scopes-per-ini.md)).

**The app's scopes** live in [winter_dragon/config.py](../../../src/winter_dragon/config.py): its own `Config[T]`, bound to `config.ini`, and `CogConfig[T]`, bound to `cogs.ini`; both are operator files. Settings are plain classes whose attributes are descriptors, with a one-line docstring each:

```python
class Settings:
    bot_name = Config("WinterDragon")
    """The bot's name."""
    created_color = Config(Hex(0x00FF00))          # confkit data types: Hex, List, Enum
```

`Settings` (`bot_name`, `support_guild_id`, `log_level`, the `created`/`changed`/`deleted` colors, `bot_status_messages`) is the app-wide class in `config.ini`. Access is static (`Settings.support_guild_id`) — reads/writes go live to the ini file. An edit to the file on disk is picked up on the next read without a restart (`Config.on_file_change` re-reads it). The colors back the confirmation embeds in [winter_dragon/ui](../../../src/winter_dragon/ui/embeds.py): a successful create/change/delete replies with `CreatedEmbed`/`ChangedEmbed`/`DeletedEmbed(description=...)`; a refusal stays plain text.

**Cog settings live with their cog**, declared with `CogConfig(...)`. Every cog shares `cogs.ini`, one section per settings class (the section name is the class name, so keep it stable): `ReminderSettings`, `StatsSettings` and `UrbanSettings` sit in their cog module, `SteamSettings` in [cogs/steam/settings.py](../../../src/winter_dragon/cogs/steam/settings.py). A new cog's settings are a class in (or next to) the cog — never a module in `wd-config`, and never a second `Config` subclass on `cogs.ini`.

**Library scopes:** `DiscordConfig[T]` binds to `discord.ini` ([wd_config/discord.py](../../../wd-config/src/wd_config/discord.py)). A new scope subclasses a `Config` and calls `.bind(file, ...)` right after the class — `bind` does `set_file` and resets the parser state `__init_subclass__` copied from the parent. wd-config's own ini paths are declared once in [wd_config/constants.py](../../../wd-config/src/wd_config/constants.py).

**`discord.ini` is internal-only; its existence is the switch.** If the file is absent when `DiscordConfig` is defined, its in-code defaults apply and nothing is written (`write_on_edit` is set from `DISCORD_CONFIG_FILE.exists()`, and an `_OptionalFileWatcher` lets reads work without the file). Create it (even empty) to expose the scope, and confkit fills in the defaults on the next start; delete it to reset. So a `DiscordConfig` setting (e.g. `RateLimit.max_retries`, `UserAgent.url`) is a developer knob, not an operator one: never require it to be set.

**Scopes live with their package:** wd-bot's `BotConfig[T]` binds to `bot.ini` in [wd_bot/settings.py](../../../wd-bot/src/wd_bot/settings.py), with `Tokens.discord_token` and `BotSettings` (`BOT_SCOPE`, `intents`, `permissions`, `auto_reload_*`). Intents and permissions are stored as ints; wrap them (`Intents(BotSettings.intents)`) when reading. The application ID is not a setting: the bot and the dashboard fetch it from Discord at startup into `ApplicationId` ([wd_bot/application.py](../../../wd-bot/src/wd_bot/application.py)); read it with `ApplicationId.get()`. wd-discord never reads `bot.ini`. wd-db's `DatabaseConfig[T]` binds to `database.ini` in [wd_db/settings.py](../../../wd-db/src/wd_db/settings.py), with `DbUrl` (`password` is `REQUIRED`) and `ApiTableSettings.request_timeout`. `SentryConfig[T]` binds to `sentry.ini` in [wd_config/sentry.py](../../../wd-config/src/wd_config/sentry.py) (it stays in wd-config because wd-discord reads `SentrySettings.Telemetry`); `SentrySettings.dsn` is `REQUIRED`, and Sentry is initialised with `SentrySettings.resolved_dsn()`, which treats `!!` as no DSN. All three are operator files: `.bind(file, operator=True)`.

| File | Scope | Owner | Kind |
| --- | --- | --- | --- |
| `config.ini` | `Config` (`Settings`) | app, `winter_dragon/config.py` | operator |
| `cogs.ini` | `CogConfig` (one section per cog settings class) | app, each cog | operator |
| `bot.ini` | `BotConfig` (`Tokens`, `BotSettings`) | wd-bot | operator (+ wd-bot internals) |
| `database.ini` | `DatabaseConfig` (`DbUrl`, `ApiTableSettings`) | wd-db | operator |
| `sentry.ini` | `SentryConfig` (`SentrySettings`) | wd-config | operator |
| `discord.ini` | `DiscordConfig` (`URLS`, `RestCache`, `RateLimit`, `UserAgent`) | wd-config | internal, only if it exists |

**Migration from the old single `config.ini`.** [`__main__.py`](../../../src/winter_dragon/__main__.py) calls `migrate_legacy_config()` ([winter_dragon/config_migration.py](../../../src/winter_dragon/config_migration.py)) before any settings class is imported, then imports `winter_dragon.config` so `config.ini`/`cogs.ini` are registered before `Bot.start` runs `OperatorFiles.check()`. The app owns the mapping (`MOVES`, one `Move` per legacy section; a whole-section move to `cogs.ini` is one line); the generic engine is `migrate(legacy, moves)` in [wd_config/migration.py](../../../wd-config/src/wd_config/migration.py). It runs only while `config.ini` still holds something to move or drop, backs the original up to `config.ini.bak` (or `.bak.1`, `.bak.2`, ... — a backup is never overwritten), fills a target key only when missing or `!!`, drops and logs undeclared sections/keys, writes an internal (`discord.ini`) value only when it differs from its default, and rewrites `config.ini` with only `[Settings]`. The mapping can't import file paths or internal defaults from the scopes (importing a scope writes its file), so `wd-config/tests/test_migration.py` pins them to the scopes. A setting added after the split never existed in the old file and needs no `Move`.

**Injecting config into functions:** the decorator form `@Config.with_kwarg("Section", "setting")` passes a config value as a kwarg (see `Bot.start` in [wd_bot/bot.py](../../../wd-bot/src/wd_bot/bot.py): `@BotConfig.with_kwarg("Tokens", "discord_token", name="token")`). Type checkers don't see the injected kwarg, so call sites carry a coded ignore — prefer it over reading config inside the function body.

## Constants

Fixed values live in the owning package's `constants.py` with a docstring:

- [wd_discord/constants.py](../../../wd-discord/src/wd_discord/constants.py) — `DISCORD_EPOCH`, the snowflake epoch.
- [wd_db/constants.py](../../../wd-db/src/wd_db/constants.py) — `CASCADE`, plus **`DATABASE_URL` assembled from the `DbUrl` config descriptors in `database.ini`**. That's the source-of-truth pattern in one line: credentials/host/port are config, the URL is derived, nothing redefines either.

**A constant taken from documentation links to it.** A single constant ends its docstring with the full URL to the section anchor: `"""An embed holds up to 25 fields (https://docs.discord.com/developers/resources/message#embed-object-embed-limits)."""`. An enum or flag mirroring documented values carries one link in its class docstring. A value from an undocumented API (Steam's store API) links the community reference and says so: `(unofficial reference: https://steamapi.xpaw.me/#IStoreQueryService/Query)`. A Discord limit a cog needs is imported from [wd_discord/limits.py](../../../wd-discord/src/wd_discord/limits.py) (`MAX_CHANNEL_NAME_LENGTH`, `MAX_EMBED_*`), never redefined, and text cut to one goes through its `truncate`. A default that's a security decision says so in its docstring (`BOT_PERMISSIONS` in [wd_core/constants.py](../../../wd-core/src/wd_core/constants.py) asks for every permission).

Discord API base + version are config (`URLS` in [wd_config/discord.py](../../../wd-config/src/wd_config/discord.py), `api_version` property renders `"v10"`) — do not hardcode `https://discord.com/api/v10` in new code.

## First-launch & unset values

[wd_config/parser.py](../../../wd-config/src/wd_config/parser.py) `OperatorFiles` owns the check and knows no settings. A scope with operator settings binds with `.bind(file, operator=True)`, which registers its file; internal-only files (`discord.ini`) don't. A required operator setting defaults to `REQUIRED` (`"!!"`), not an empty string, so confkit writes `!!` on first launch; `required(hint)` writes `!! <hint>` instead, for a pointer to where the value comes from (the dashboard's `client_secret` names the developer-portal page). Any value starting with `!!` counts as unset (`is_required`). `Bot.start` calls `OperatorFiles.check()` before connecting, which raises `FirstTimeLaunchError` listing each `file:section:key` still at `!!`; `OperatorFiles.unset()` yields the same entries.

## Rules of thumb

- Adding a setting → the matching class of the owning scope (app `Settings`, the cog's settings class, or the library package's), with a sensible default so first launch works.
- Adding a fixed protocol value → `constants.py` of the package that owns the protocol.
- Reading a setting from another package → import the settings class; never re-read the ini yourself and never copy the value.
