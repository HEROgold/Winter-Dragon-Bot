---
name: config-and-constants
description: Where configurable values, constants, and derived settings live in WinterDragonV2 (confkit Config descriptors, config.ini/discord.ini/bot.ini/database.ini/sentry.ini, Settings classes). Use when adding a setting, a constant, an env-like value, a URL/port/token, or when unsure what the source of truth for a value is.
---

# Config, constants & source of truth

Configuration is the **confkit descriptor system** — not `os.environ`, not dotenv, not hardcoded literals. Every value has exactly one owner; everything else imports or derives from it.

## The decision

- **Can an operator ever want to change it?** → a `Config` descriptor in `wd-config`.
- **Is it fixed by a protocol/spec?** (Discord epoch, header names, SQL keywords) → a module constant in the owning package's `constants.py`.
- **Is it computed from other settings?** → a `Combined` data type, never a second literal.

## Configurable values: `Config[T]` descriptors

[wd_config/config.py](../../../wd-config/src/wd_config/config.py) defines `class Config[T](CKConfig[T])` bound to `config.ini` via `Config.set_file(CONFIG_FILE)`. Settings are plain classes whose attributes are descriptors:

```python
class Settings:
    log_level = Config(logging.DEBUG)
    bot_name = Config("WinterDragon")
    created_color = Config(Hex(0x00FF00))          # confkit data types: Hex, List, Enum
```

Surfaces, one class per concern: `Settings` ([bot.py](../../../wd-config/src/wd_config/bot.py)), plus per-cog `ReminderSettings`, `SteamSettings`, `UrbanSettings` — the full list with attributes is [docs/reference/wd-config.md](../../../docs/reference/wd-config.md). A new cog's settings get their own module + class there. Access is static (`Settings.bot_name`) — reads/writes go live to the ini file.

**Second scope:** `DiscordConfig[T]` binds to `discord.ini` ([wd_config/discord.py](../../../wd-config/src/wd_config/discord.py)). Gotcha: after `set_file`, it must reset `_parser = UNSET` and `_has_read_config = False` because `__init_subclass__` copies parent parser state — copy that block if you ever add a third scope. Both ini paths are declared once in [wd_config/constants.py](../../../wd-config/src/wd_config/constants.py).

**`discord.ini` is internal-only; its existence is the switch.** If the file is absent when `DiscordConfig` is defined, its in-code defaults apply and nothing is written (`write_on_edit` is set from `DISCORD_CONFIG_FILE.exists()`, and an `_OptionalFileWatcher` lets reads work without the file). Create it (even empty) to expose the scope, and confkit fills in the defaults on the next start; delete it to reset. So a `DiscordConfig` setting (e.g. `RateLimit.max_retries`, `UserAgent.url`) is a developer knob, not an operator one: never require it to be set.

**Scopes live with their package:** wd-bot's `BotConfig[T]` binds to `bot.ini` in [wd_bot/settings.py](../../../wd-bot/src/wd_bot/settings.py), with `Tokens.discord_token` and `BotSettings` (`application_id`, `BOT_SCOPE`, `intents`, `permissions`, `auto_reload_*`). Intents and permissions are stored as ints; wrap them (`Intents(BotSettings.intents)`) when reading. wd-discord never reads `bot.ini`: wd-bot passes `application_id` into `Client`. wd-db's `DatabaseConfig[T]` binds to `database.ini` in [wd_db/settings.py](../../../wd-db/src/wd_db/settings.py), with `DbUrl` (`password` is `REQUIRED`) and `ApiTableSettings.request_timeout`. `SentryConfig[T]` binds to `sentry.ini` in [wd_config/sentry.py](../../../wd-config/src/wd_config/sentry.py) (it stays in wd-config because wd-discord reads `SentrySettings.Telemetry`); `SentrySettings.dsn` is `REQUIRED`, and Sentry is initialised with `SentrySettings.resolved_dsn()`, which treats `!!` as no DSN. All three are operator files: `.bind(file, operator=True)`.

**Injecting config into functions:** the decorator form `@Config.with_kwarg("Section", "setting")` passes a config value as a kwarg (see `Bot.start` in [wd_bot/bot.py](../../../wd-bot/src/wd_bot/bot.py): `@BotConfig.with_kwarg("Tokens", "discord_token", name="token")`). Type checkers don't see the injected kwarg, so call sites carry a coded ignore — prefer it over reading config inside the function body.

## Derived values: `Combined`

Never repeat a fragment of another setting. Compose:

```python
WEBSITE_URL = Config(Combined(PROTOCOL_PREFIX, SERVER_IP, ":", WEBSITE_PORT))
DATETIME_FORMAT = Config(Combined(DATE_FORMAT, " ", TIME_FORMAT))
```

`Combined` ([data_types.py](../../../wd-config/src/wd_config/data_types.py)) stringifies constituent `Config` descriptors at read time, so derived values track their parts automatically.

## Constants

Fixed values live in the owning package's `constants.py` with a docstring:

- [wd_discord/constants.py](../../../wd-discord/src/wd_discord/constants.py) — `DISCORD_EPOCH`, `RATE_LIMIT_BUCKET` header name.
- [wd_db/constants.py](../../../wd-db/src/wd_db/constants.py) — `CASCADE`, plus **`DATABASE_URL` assembled from the `DbUrl` config descriptors in `database.ini`**. That's the source-of-truth pattern in one line: credentials/host/port are config, the URL is derived, nothing redefines either.

Discord API base + version are config (`URLS` in [wd_config/discord.py](../../../wd-config/src/wd_config/discord.py), `api_version` property renders `"v10"`) — do not hardcode `https://discord.com/api/v10` in new code.

## First-launch & unset values

[wd_config/parser.py](../../../wd-config/src/wd_config/parser.py) `OperatorFiles` owns the check and knows no settings. A scope with operator settings registers its file next to its `set_file` with one line, `OperatorFiles.register(BOT_CONFIG_FILE)`; internal-only files (`discord.ini`) don't. A required operator setting defaults to `REQUIRED` (`"!!"`), not an empty string, so confkit writes `!!` on first launch. `Bot.start` calls `OperatorFiles.check()` before connecting, which raises `FirstTimeLaunchError` listing each `file:section:key` still at `!!`; `OperatorFiles.unset()` yields the same entries.

## Rules of thumb

- Adding a setting → the matching class in `wd-config`, with a sensible default so first launch works.
- Adding a fixed protocol value → `constants.py` of the package that owns the protocol.
- Reading a setting from another package → import the settings class; never re-read the ini yourself and never copy the value.
