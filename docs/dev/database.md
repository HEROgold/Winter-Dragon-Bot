# Database

Winter Dragon stores its data with [SQLModel](https://sqlmodel.tiangolo.com/) on PostgreSQL. Tests and
`winter_dragon.run_test_bot` use sqlite instead.

## Connection

- The connection URL is assembled from the `DbUrl` settings in `database.ini` (`wd_db.settings`) into
  `wd_db.constants.DATABASE_URL`.
- `wd_db.constants` creates the process-wide `engine` and `session` when it is imported, so PostgreSQL needs
  the psycopg driver installed.
- Cogs receive a session through `BotArgs["db_session"]` and fall back to the shared engine. Tests pass an
  in-memory sqlite session instead.

## Defining tables

Each table is a `SQLModel` class with `table=True`, declared by the feature that owns it. A cog creates its
tables in its `load` hook:

```python
class Fuel(GroupCog, name="fuel", description="Track your car's refuels and fuel efficiency"):
    @override
    async def load(self) -> None:
        """Create the refuel table if missing."""
        self.create_tables(CarFuels)
```

Each table is named after its model in lower case. `Cog.create_tables` (`wd_db.schema.ensure_tables`) only
checks the tables exist in a database the migrations manage, and raises `UnmigratedTablesError` for a missing
one: the [migration](#migrations) creates it. In any other database (the sqlite test bot, tests) it creates the
missing tables itself.

Base classes in `wd_db.extension.model`:

- `SQLModel` — the base for a plain table.
- `DiscordID` — a table keyed by a Discord ID.
- `BaseModel` — repository helpers (`add`, `update`, `get`, `get_all`, `delete`, `fetch`). Every subclass is
  registered automatically.

Link one model to another with `herogold.orm.Relationship`, but read and set the link with
`wd_db.extension.relationships` (`linked(session, row, "name")`, `link(session, row, "name", target)`). Assigning
through the descriptor (`row.name = target`) writes through herogold's own session and commits at once
([HeroPy#56](https://github.com/HEROgold/HeroPy/issues/56)), outside your transaction.

## Current tables

| Table | Owner | Purpose |
|---|---|---|
| `CarFuels` | `winter_dragon.cogs.fuel` | Refuel log per user. |
| `Reminder`, `TimedReminder` | `winter_dragon.cogs.reminder` | One-off and repeating reminders. |
| `SteamSale`, `SteamSaleProperties`, `SteamUsers` | `winter_dragon.cogs.steam.models` | Known Steam sales and the users subscribed to them. |
| `ApiTable`, `RiotTournaments` | `wd_db.extension.api_table` | Legacy, used only by `wd-cogs`. |
| `archive_*` | `archive.models` | Every gateway event the [archive](../spec/archive.md) received, and the objects they carried. |

Each table's columns are listed as `fields` in the [API reference](../reference/index.md).

## Migrations

The schema's history is the Alembic revisions in `src/winter_dragon/migrations/versions/`; the models are the
source of truth ([ADR 0004](../adr/0004-alembic-migrations-applied-on-start.md)).

**Changing a table.** Edit the model and open a PR. The **Auto-migrate** workflow
([HEROgold/auto-migrate-pr](https://github.com/HEROgold/auto-migrate-pr)) autogenerates the revision on the PR's
head and opens it as a migration PR stacked on yours (`migration/<branch>` into `<branch>`); each push regenerates
it. Review it, fix it there (commits you push to it are kept, and the workflow stops regenerating), and merge it into
your branch. In a stack of PRs, merge the lower PR's migration and rebase before the upper one is generated, so the
revisions stay one line. The **Test** workflow's `migrations` job is required on `main`, so a PR whose models no
revision covers can't merge.

To autogenerate a revision yourself, run it against a scratch Postgres, never the live database (`revision`
upgrades the database it's given first):

```bash
docker run -d --rm --name wd-scratch -e POSTGRES_PASSWORD=scratch -p 55432:5432 postgres:14-alpine
uv run python -m winter_dragon.migrations --url postgresql://postgres:scratch@localhost:55432/postgres revision -m "add reminder snooze"
docker stop wd-scratch
```

Read the generated file before committing it: autogenerate misses renames (it writes a drop and an add, losing the
column's data) and leaves Postgres enum types behind on downgrade. CI's **Test** workflow applies every revision to
an empty Postgres, fails when the models have changes no revision covers (`check`), and undoes and reapplies them.

**Applying them.** `docker compose up -d` runs `backup` (a dump), then `migrate`
(`python -m winter_dragon.migrations upgrade`), and only then starts `bot` and `web`. A failed migration rolls back
whole and keeps the bot and web from starting; the error is in `docker compose logs migrate`. A restart of `bot` or
`web` alone, or Docker restarting them, doesn't migrate, so pull new code with `git pull && docker compose up -d --build`.

A database the bot built before migrations existed is adopted on its first `upgrade`: it's marked as at the baseline
and the next revision reconciles the differences.

Other commands: `check`, `current`, `downgrade <target>` (e.g. `-1`), each with an optional `--url`.

## Backups

Dumps (pg_dump's custom format) land in `./backups/`, which git ignores:

- `pre-migrate-<time>.dump` on every `docker compose up`, before the migrations run;
- `daily-<time>.dump` once a day from the `backup-daily` service.

The newest 14 of each kind are kept (`scripts/backup-db.sh`). To restore one, stop what writes to the database and
load the dump:

```bash
docker compose stop bot web
docker compose run --rm -T backup pg_restore --clean --if-exists -d winter_dragon /backups/<file>.dump
docker compose up -d
```

## Operations

```bash
docker compose exec postgres psql -U postgres winter_dragon      # shell
docker compose logs migrate                                      # the last migration run
docker compose run --rm migrate python -m winter_dragon.migrations current
```

pgAdmin runs at <http://localhost:5050> (see [Setup](setup.md#run) for logins).
