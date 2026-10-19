<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_db` (wd-db)
The database package for the Winter Dragon project.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_db` — `wd-db/src/wd_db/__init__.py`

- exports: SQLModel, SessionMixin, session

## `wd_db.channel_types` — `wd-db/src/wd_db/channel_types.py`
Module containing tags for the database.

### `class Tags(Enum)`
Enum containing available tags for the database.

- attributes: UNKNOWN, STATS, LOGS, TICKETS, TEAM_VOICE, TEAM_CATEGORY, TEAM_LOBBY

## `wd_db.check_tables` — `wd-db/src/wd_db/check_tables.py`
Check that every table Class is present.

- module names: GREEN, YELLOW, RED, RESET
- `find_table_classes(py_path: Path) -> list[str]` — Find all class names in the given Python file that define SQLModel tables.
- `load_all_list(init_path: Path) -> list[str]` — Load the __all__ list from the given __init__.py file.
- `main() -> int` — Entry point.

## `wd_db.constants` — `wd-db/src/wd_db/constants.py`
Module for containing constants and configuration for the database package.

- module names: CASCADE, DATABASE_URL, engine, session

### `class SessionMixin`
Mixin class to provide a session for database operations.

- fields: session: Session

## `wd_db.keys` — `wd-db/src/wd_db/keys.py`
Module with helper methods for the database package.

- `get_foreign_key(table: type[SQLModel], column: str='id') -> str` — Get the foreign key for a given table and column.

## `wd_db.schema` — `wd-db/src/wd_db/schema.py`
Making sure a model's tables exist: the migrations own a database they manage, anything else is created on the spot.

- module names: MIGRATIONS_TABLE
- `managed_by_migrations(bind: Engine | Connection) -> bool` — Return whether the migrations manage ``bind``'s database.
- `ensure_tables(bind: Engine | Connection, *models: type[SQLModel]) -> None` — Make sure the tables of ``models`` exist in ``bind``; each is named after its model, lowercased.

### `class UnmigratedTablesError(RuntimeError)`
Tables a model defines are missing from a database the migrations manage.

## `wd_db.settings` — `wd-db/src/wd_db/settings.py`
wd-db's settings, backed by their own database.ini file.

- module names: DATABASE_CONFIG_FILE

### `class DatabaseConfig[T](Config[T])`
Config descriptor scoped to the database settings file.

### `class DbUrl`
The database URL components; ``wd_db.constants.DATABASE_URL`` is assembled from them.

- attributes: driver_name, database, username, password, host, port

### `class ApiTableSettings`
How :class:`wd_db.extension.api_table.ApiTable` talks to external APIs.

- attributes: request_timeout
