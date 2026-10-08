# Winter Dragon Bot

A Discord bot with moderation, utility and entertainment features. The `v2` branch is a rewrite on an in-house
Discord API client (`wd-discord`) instead of discord.py, split into `wd-*` packages in one uv workspace.

## Quick start

```bash
uv sync
uv run python -m winter_dragon.run_test_bot   # first run writes config.ini: fill in every !! value, then rerun
uv run python -m winter_dragon                # the real bot, on PostgreSQL (docker compose up -d postgres redis)
uv run pytest -q
```

## Layout

| Path | What |
|---|---|
| `src/winter_dragon/` | The app: entry point and the live cogs (`cogs/`). |
| `wd-bot/` | Bot framework: `Bot`, `Cog`, commands, components, command sync. |
| `wd-discord/` | Discord API v10 client: REST, gateway, models, entities. |
| `wd-config/`, `wd-db/`, `wd-core/`, `wd-errors/`, `wd-types/` | Config, database, shared helpers, errors, types. |
| `wd-cogs/` | Legacy discord.py-era cogs waiting to be ported. |
| `docs/` | Zensical docs; `docs/reference/` is generated from source. |

## Documentation

Online at <https://herogold.github.io/Winter-Dragon-Bot>. Locally:

```bash
uv sync --group docs
uv run zensical serve
```

- [Getting Started](docs/guide/getting-started.md) — run an instance, list of commands
- [Architecture](docs/dev/architecture.md) — packages, layering, runtime flow
- [Development Setup](docs/dev/setup.md) — environment, adding a cog, tests, code quality
- [Database](docs/dev/database.md) — connection, tables
- [API Reference](docs/reference/index.md) — public API of every package
- [Planned](docs/planned.md) — web dashboard, HTTP API, workers (not built yet)

## License

MIT — see [LICENSE.md](LICENSE.md).
