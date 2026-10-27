<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon.migrations` (winter-dragon)
The database's schema history: Alembic revisions in ``versions/``, run by ``python -m winter_dragon.migrations``.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.migrations` — `src/winter_dragon/migrations/__init__.py`

- module names: BASELINE
- `adopt_premigration_database(config: Config, connection: Connection) -> bool` — Mark a database the bot built before migrations existed as at :data:`BASELINE`; return whether it was one.
- `alembic_config(connection: Connection) -> Config` — Return the Alembic configuration for this package's revisions, running them on ``connection``.
- `include_object(obj: SchemaItem, name: str | None, type_: str, _reflected: bool, _compare_to: SchemaItem | None) -> bool` — Leave herogold's custom-data side tables out, except the archive's: every model declares one, only it uses them.
- `render_item(type_: str, obj: object, _autogen_context: AutogenContext) -> str | Literal[False]` — Write a wrapper column type (``AwareDateTime``, sqlmodel's ``AutoString``) as the SQLAlchemy type it stores.

## `winter_dragon.migrations.env` — `src/winter_dragon/migrations/env.py`
Alembic environment: compares the database with every table the app's cogs and the archive define.

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

## `winter_dragon.migrations.versions.2026_10_22_c9b4b18ba344_add_the_archive_s_tables` — `src/winter_dragon/migrations/versions/2026_10_22_c9b4b18ba344_add_the_archive_s_tables.py`
add the archive's tables.

- module names: revision: str, down_revision: str | None, branch_labels: str | None, depends_on: str | None
- `upgrade() -> None` — Apply this revision.
- `downgrade() -> None` — Undo this revision.

## `winter_dragon.migrations.versions.2026_10_26_5b7094b12d2c_sale_notification_log_and_steam_profile_` — `src/winter_dragon/migrations/versions/2026_10_26_5b7094b12d2c_sale_notification_log_and_steam_profile_.py`
Sale notification log and Steam profile page.

- module names: revision: str, down_revision: str | None, branch_labels: str | None, depends_on: str | None
- `upgrade() -> None` — Apply this revision.
- `downgrade() -> None` — Undo this revision.

## `winter_dragon.migrations.versions.2026_10_26_bc19dfc865e9_fuel_units_setting` — `src/winter_dragon/migrations/versions/2026_10_26_bc19dfc865e9_fuel_units_setting.py`
Fuel units setting.

- module names: revision: str, down_revision: str | None, branch_labels: str | None, depends_on: str | None
- `upgrade() -> None` — Apply this revision.
- `downgrade() -> None` — Undo this revision.

## `winter_dragon.migrations.versions.2026_10_26_c599311115ab_compatibility_checks_and_love_profile_` — `src/winter_dragon/migrations/versions/2026_10_26_c599311115ab_compatibility_checks_and_love_profile_.py`
Compatibility checks and Love profile page.

- module names: revision: str, down_revision: str | None, branch_labels: str | None, depends_on: str | None
- `upgrade() -> None` — Apply this revision.
- `downgrade() -> None` — Undo this revision.

## `winter_dragon.migrations.versions.2026_10_26_cfb33b25e168_refuel_date` — `src/winter_dragon/migrations/versions/2026_10_26_cfb33b25e168_refuel_date.py`
Refuel date.

- module names: revision: str, down_revision: str | None, branch_labels: str | None, depends_on: str | None
- `upgrade() -> None` — Apply this revision.
- `downgrade() -> None` — Undo this revision.
