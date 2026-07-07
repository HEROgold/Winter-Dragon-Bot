---
name: config-and-constants
description: Where configurable values, constants, and derived settings live in WinterDragonV2 (confkit Config descriptors, config.ini/discord.ini, Settings classes). Use when adding a setting, a constant, an env-like value, a URL/port/token, or when unsure what the source of truth for a value is.
---

# Config, constants & source of truth

Configuration is the **confkit descriptor system** — not `os.environ`, not dotenv, not hardcoded literals. Every value has exactly one owner; everything else imports or derives from it.

## The decision

- **Can an operator ever want to change it?** → a `Config` descriptor in `wd-config`.
- **Is it fixed by a protocol/spec?** (Discord epoch, header names, SQL keywords) → a module constant in the owning package's `constants.py`.
- **Is it computed from other settings?** → a `Combined` data type, never a second literal.

## Configurable values: `Config[T]` descriptors

[wd-config/src/wd_config/config.py](../../../wd-config/src/wd_config/config.py) defines `class Config[T](CKConfig[T])` bound to `config.ini` via `Config.set_file(CONFIG_FILE)`. Settings are plain classes whose attributes are descriptors:

```python
class Settings:
    log_level = Config(logging.DEBUG)
    application_id = Config[int | None](None)
    created_color = Config(Hex(0x00FF00))          # confkit data types: Hex, List, Enum
```

Surfaces: `Settings` ([bot.py](../../../wd-config/src/wd_config/bot.py)), `DbUrl` ([db.py](../../../wd-config/src/wd_config/db.py)), `SentrySettings` ([sentry.py](../../../wd-config/src/wd_config/sentry.py)). Access is static (`Settings.BOT_SCOPE`) — reads/writes go live to the ini file.

**Second scope:** `DiscordConfig[T]` binds to `discord.ini` ([discord.py:13](../../../wd-config/src/wd_config/discord.py#L13)). Gotcha: after `set_file`, it must reset `_parser = UNSET` and `_has_read_config = False` because `__init_subclass__` copies parent parser state — copy that block if you ever add a third scope. Both ini paths are declared once in [wd_config/constants.py](../../../wd-config/src/wd_config/constants.py).

**Injecting config into functions:** the decorator form `@Config.with_kwarg("Tokens", "discord_token")` passes a config value as a kwarg (see `WinterDragon.start` in [wd-bot/src/wd_bot/bot.py](../../../wd-bot/src/wd_bot/bot.py)) — prefer it over reading config inside the function body.

## Derived values: `Combined`

Never repeat a fragment of another setting. Compose:

```python
WEBSITE_URL = Config(Combined(PROTOCOL_PREFIX, SERVER_IP, ":", WEBSITE_PORT))
DATETIME_FORMAT = Config(Combined(DATE_FORMAT, " ", TIME_FORMAT))
```

`Combined` ([data_types.py](../../../wd-config/src/wd_config/data_types.py)) stringifies constituent `Config` descriptors at read time, so derived values track their parts automatically.

## Constants

Fixed values live in the owning package's `constants.py` with a docstring:

- [wd-discord/src/wd_discord/constants.py](../../../wd-discord/src/wd_discord/constants.py) — `DISCORD_EPOCH`, `RATE_LIMIT_BUCKET` header name.
- [wd-db/src/wd_db/constants.py](../../../wd-db/src/wd_db/constants.py) — `CASCADE`, plus **`DATABASE_URL` assembled from the `DbUrl` config descriptors**. That's the source-of-truth pattern in one line: credentials/host/port are config, the URL is derived, nothing redefines either.

Discord API base + version are config (`URLS` in [wd_config/discord.py:24](../../../wd-config/src/wd_config/discord.py#L24), `api_version` property renders `"v10"`) — do not hardcode `https://discord.com/api/v10` in new code.

## First-launch & unset values

[wd_config/parser.py](../../../wd-config/src/wd_config/parser.py): on first run the `ConfigParser` subclass creates the ini, writes defaults with the `"!!"` sentinel (e.g. `[Tokens] discord_token = !!`), and raises `FirstTimeLaunchError`. `is_valid()` / `get_invalid()` treat `"!!"` as "operator must fill this in". New required-but-secret settings should default to `"!!"`, not an empty string.

## Rules of thumb

- Adding a setting → the matching class in `wd-config`, with a sensible default so first launch works.
- Adding a fixed protocol value → `constants.py` of the package that owns the protocol.
- Reading a setting from another package → import the settings class; never re-read the ini yourself and never copy the value.
