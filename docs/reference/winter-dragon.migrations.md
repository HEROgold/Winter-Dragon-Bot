<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon.migrations` (winter-dragon)
The database's schema history: Alembic revisions in ``versions/``, run by ``python -m winter_dragon.migrations``.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.migrations` — `src/winter_dragon/migrations/__init__.py`

- module names: BASELINE
- `adopt_premigration_database(config: Config, connection: Connection) -> bool` — Mark a database the bot built before migrations existed as at :data:`BASELINE`; return whether it was one.
- `alembic_config(connection: Connection) -> Config` — Return the Alembic configuration for this package's revisions, running them on ``connection``.
- `include_object(_obj: SchemaItem, name: str | None, type_: str, _reflected: bool, _compare_to: SchemaItem | None) -> bool` — Leave herogold's custom-data side tables out: every model declares one, and the bot uses none of them.
- `render_item(type_: str, obj: object, _autogen_context: AutogenContext) -> str | Literal[False]` — Write a wrapper column type (``AwareDateTime``, sqlmodel's ``AutoString``) as the SQLAlchemy type it stores.

## `winter_dragon.migrations.env` — `src/winter_dragon/migrations/env.py`
Alembic environment: compares the database with every table the app's cogs define.

- module names: connection

## `winter_dragon.migrations.versions.2026_10_19_2a9de84f886e_baseline_every_table_the_cogs_define` — `src/winter_dragon/migrations/versions/2026_10_19_2a9de84f886e_baseline_every_table_the_cogs_define.py`
baseline: every table the cogs define.

- module names: revision: str, down_revision: str | None, branch_labels: str | None, depends_on: str | None
- `upgrade() -> None` — Apply this revision.
- `downgrade() -> None` — Undo this revision.

## `winter_dragon.migrations.versions.2026_10_19_e53d62945ef6_reconcile_databases_made_before_` — `src/winter_dragon/migrations/versions/2026_10_19_e53d62945ef6_reconcile_databases_made_before_.py`
Reconcile databases made before migrations with the baseline.

- module names: revision: str, down_revision: str | None, branch_labels: str | None, depends_on: str | None,
  LIFECYCLE_TABLES, PRIMARY_KEY_INDEXES, UNUSED_TABLES
- `upgrade() -> None` — Make a pre-migration database match the baseline.
- `downgrade() -> None` — Nothing to undo: the baseline is what this revision brings a database to.
