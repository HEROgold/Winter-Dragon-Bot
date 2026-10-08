# Development Setup

## Prerequisites

- Python 3.15 and [uv](https://docs.astral.sh/uv/) (uv installs the interpreter if it's missing)
- Docker, for PostgreSQL and the other infrastructure services
- A Discord application with a bot token

## Install

```bash
git clone https://github.com/HEROgold/Winter-Dragon-Bot.git
cd Winter-Dragon-Bot
git checkout v2
uv sync
uvx pre-commit install
```

`uv sync` installs every workspace package in editable mode. Change dependencies only with
`uv add --package <wd-member> <requirement>`, never by editing `pyproject.toml` or `uv.lock` by hand.

## Configure

Configuration lives in `config.ini` (bot) and `discord.ini` (Discord API), not environment variables. On the
first run the bot writes both files with defaults and stops with `FirstTimeLaunchError`. Every value shown as
`!!` must be filled in, for example `[Tokens] discord_token`. All settings and their defaults are in the
[`wd_config` reference](../reference/wd-config.md).

## Run

```bash
# Infrastructure only: postgres, redis and the admin UIs
docker compose up -d postgres redis redis-commander pgadmin grafana

# The bot, against the configured PostgreSQL database
uv run python -m winter_dragon

# Or a time-boxed live bot on a local sqlite database (stops after 10 minutes)
uv run python -m winter_dragon.run_test_bot
```

| Service | URL | Default login |
|---|---|---|
| pgAdmin | <http://localhost:5050> | `admin@example.com` / `admin123` |
| Grafana | <http://localhost:3002> | `admin` / `admin123` |
| Redis Commander | <http://localhost:8081> | — |

PostgreSQL is only reachable inside the compose network: `docker compose exec postgres psql -U postgres winter_dragon`.

## Adding a feature

A feature is a cog module in `src/winter_dragon/cogs/`. The bot discovers it automatically.

```python
"""The /uptime command group: how long the bot has been running."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_bot.cogs import Cog, GroupCog


if TYPE_CHECKING:
    lazy from wd_discord import CommandInteraction


class Uptime(GroupCog, name="uptime", description="Show how long the bot has been running"):
    """Cog for showing the bot's uptime."""

    @Cog.command(name="bot", description="Show the bot's current uptime")
    async def bot_uptime(self, interaction: CommandInteraction) -> None:
        """Reply with when the bot started."""
        await interaction.respond(f"Online since {self.bot.launch_time}")
```

- Database tables are `SQLModel` classes with `table=True`, declared next to the cog. The cog creates them
  with `self.create_tables(Model)` (see `winter_dragon/cogs/fuel.py`).
- Settings go in a new class in `wd-config` (see `SteamSettings`, `UrbanSettings`).
- Buttons use `@Cog.component(prefix)`, gateway events use `@Cog.listener`.

## Test

```bash
uv run pytest -q                       # whole suite
uv run pytest wd-bot/tests -k steam -q # one area
```

Cog tests live in `wd-bot/tests/`; wd-discord tests in `wd-discord/tests/`. Offline tests use
`wd_discord.testing.RecordingClient` and an in-memory sqlite session. Tests marked `integration` hit the real
Discord API and skip unless a token is configured.

## Code quality

Pre-commit runs ruff (all rules), strict pyrefly with a baseline, the doc-link check, and the generated-file
checks. To run the main ones by hand:

```bash
uv run ruff check . --fix
uv run ruff format .
uvx pyrefly check src wd-bot/src wd-cogs/src wd-config/src wd-core/src wd-db/src wd-discord/src wd-errors/src wd-types/src --baseline pyrefly-baseline.json
uv run python scripts/generate_api_reference.py   # after changing any public API
```

## Docs

```bash
uv sync --group docs
uv run zensical serve
```

`docs/reference/` is generated. Don't edit it; rerun `scripts/generate_api_reference.py`.
