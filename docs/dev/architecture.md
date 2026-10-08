# Architecture

Winter Dragon v2 is a Discord bot built on its own Discord client instead of discord.py. The code is a
[uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): eight `wd-*` library packages plus
the app itself in `src/winter_dragon/`.

## Packages and layering

Dependencies only point downward. A package never imports one above it.

```text
wd-types            wd-config             ← no internal dependencies
                    /       \
                wd-db      wd-discord     ← infrastructure
                   \       /    \
                    \  wd-core  wd-errors ← shared domain helpers, error machinery
                     \    |     /
                       wd-bot             ← bot framework
                          |
                    winter_dragon         ← the app: entry point + feature cogs
```

| Package | Owns |
|---|---|
| `wd-config` | Every configurable value, as confkit `Config[T]` descriptors bound to `config.ini` / `discord.ini`. |
| `wd-discord` | The Discord API v10 client: REST transport, gateway, pydantic response models, client-bound entities. |
| `wd-db` | SQLModel/SQLAlchemy engine and session, model base classes. |
| `wd-core` | Audit-log events, gateway intents, Sentry setup, an HTTP client for third-party APIs. |
| `wd-errors` | Error base classes and the self-registering error-handler factory. |
| `wd-types` | Cross-package protocols and type aliases. |
| `wd-bot` | `Bot`, `Cog`/`GroupCog`, slash commands, components, autocomplete, help, command sync. |
| `winter_dragon` | `python -m winter_dragon` and the live cogs in `src/winter_dragon/cogs/`. |
| `wd-cogs` | **Legacy** discord.py-era cogs, not loaded. Port a cog into `winter_dragon/cogs/` before using it. |

Each package's public API is listed in the [API reference](../reference/index.md).

## Runtime flow

1. `python -m winter_dragon` builds `Bot(extensions_package=winter_dragon.cogs)` and awaits `Bot.start()`.
   The bot token is injected from `config.ini` (`[Tokens] discord_token`) by `@Config.with_kwarg`.
2. `Bot` discovers every cog module in the extensions package, instantiates each `Cog` with the bot and a
   database session, and creates the tables the cog declares (`Cog.create_tables`).
3. Application commands are synced with Discord. The sync state is stored in the database so unchanged
   commands aren't pushed again (`wd_bot.auto_sync`).
4. The gateway connection (`wd_discord.gateway`) receives dispatch events. `parse_dispatch` validates each one
   into a model, and `wd_discord.bind` wraps it in an entity bound to the client: a `Message`, a `Guild`,
   a typed `Interaction`.
5. `Bot` routes the result. Interactions go to the matching `@Cog.command`, `@Cog.component` or
   autocomplete handler. Other events go to `@Cog.listener` methods.

## Design rules

- **Errors are values.** wd-discord operations return `T | NetworkError` instead of raising, and callers
  narrow with `is_network_error`.
- **Validated models.** Every Discord response is a pydantic `DiscordModel`. Unknown fields are kept and
  reported to Sentry instead of being dropped.
- **No bare primitives.** IDs are `Snowflake`, tokens are `Token`, flags are `IntFlag`s.
- **Constructor injection.** Cogs receive the bot and session; tests inject a sqlite session and a
  `RecordingClient`.

The full rules agents follow live in `.claude/skills/` (architecture, code-style, discord-api-models,
value-modeling, config-and-constants).

## Infrastructure

`docker-compose.yml` provides PostgreSQL, Redis, pgAdmin, Grafana and Redis Commander. The `bot` service
runs `python -m winter_dragon`. The `api` and `workers` services point at modules that don't exist yet —
see [Planned](../planned.md).
