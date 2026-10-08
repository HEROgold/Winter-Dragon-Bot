# Winter Dragon

**Winter Dragon** is a Discord bot with moderation, utility and entertainment features. These docs cover the
`v2` rewrite: the bot runs on its own Discord API client (`wd-discord`) instead of discord.py, split into
`wd-*` packages in one uv workspace.

## Quick start

```bash
uv sync
uv run python -m winter_dragon.run_test_bot   # first run writes config.ini; fill in the !! values
```

The full steps are in [Getting Started](guide/getting-started.md).

## Documentation

- **[Getting Started](guide/getting-started.md)** — run your own instance and see its commands.
- **[Feature Inventory](features/index.md)** — everything the bot offers on `main`, and how much is ported to `v2`.
- **[Architecture](dev/architecture.md)** — packages, layering and the runtime flow.
- **[Setup](dev/setup.md)** — development environment, adding a cog, tests and code quality.
- **[Database](dev/database.md)** — connection, how tables are declared, current tables.
- **[API Reference](reference/index.md)** — the public classes and functions of every package, generated from source.
- **[Planned](planned.md)** — the web dashboard, HTTP API and workers, which aren't built yet.

## Technology

Python 3.15 with uv · `wd-discord` (httpxyz + websockets + pydantic) · SQLModel on PostgreSQL · confkit
configuration · Sentry · Docker Compose for PostgreSQL, Redis, pgAdmin and Grafana.

## License

MIT — see [LICENSE.md](https://github.com/HEROgold/Winter-Dragon-Bot/blob/v2/LICENSE.md).
