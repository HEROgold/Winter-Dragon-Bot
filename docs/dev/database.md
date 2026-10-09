# Database

Winter Dragon stores its data with [SQLModel](https://sqlmodel.tiangolo.com/) on PostgreSQL. Tests and
`winter_dragon.run_test_bot` use sqlite instead.

## Connection

- The connection URL is assembled from the `DbUrl` settings in `config.ini` (`wd_config.db`) into
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

`Cog.create_tables` creates only the tables that are missing. Each table is named after its model in lower
case. There are no migrations yet, so changing a column on an existing table means migrating it by hand.

Base classes in `wd_db.extension.model`:

- `SQLModel` — the base for a plain table.
- `DiscordID` — a table keyed by a Discord ID.
- `BaseModel` — repository helpers (`add`, `update`, `get`, `get_all`, `delete`, `fetch`). Every subclass is
  registered automatically.

## Current tables

| Table | Owner | Purpose |
|---|---|---|
| `CarFuels` | `winter_dragon.cogs.fuel` | Refuel log per user. |
| `Reminder`, `TimedReminder` | `winter_dragon.cogs.reminder` | One-off and repeating reminders. |
| `SteamSale`, `SteamSaleProperties`, `SteamUsers` | `winter_dragon.cogs.steam.models` | Known Steam sales and the users subscribed to them. |
| `ApiTable`, `RiotTournaments` | `wd_db.extension.api_table` | Legacy, used only by `wd-cogs`. |

Each table's columns are listed as `fields` in the [API reference](../reference/index.md).

## Operations

```bash
docker compose exec postgres psql -U postgres winter_dragon      # shell
docker compose exec -T postgres pg_dump -U postgres winter_dragon > backup.sql
docker compose exec -T postgres psql -U postgres winter_dragon < backup.sql
```

pgAdmin runs at <http://localhost:5050> (see [Setup](setup.md#run) for logins).
