# wd-db

Database access on SQLModel/SQLAlchemy: the process-wide `engine`/`session` (built from `DbUrl` config), `SessionMixin`, and the model bases.

- **Depends on:** wd-config, wd-types (plus sqlmodel, sqlalchemy, psycopg, herogold).
- **Start here:** `wd_db.extension.model` — `BaseModel` is a repository (`add/update/get/get_all/delete/fetch`) that auto-registers every subclass; `SQLModel` and `DiscordID` are the older bases. New bot tables use `wd_db.extension.lifecycle`'s `LifecycleModel` (timestamps, soft delete, a declared `Ownership`), read through `alive(...)`, and write through `create_or_restore`/`soft_delete`. `wd_db.constants` holds `DATABASE_URL`, `engine`, `session`. `wd_db.schema.ensure_tables` is how a cog makes sure its tables exist: it creates them, except in a database the migrations (`winter_dragon.migrations`) manage, where it only checks.
- **Gotcha:** importing `wd_db.constants` creates a Postgres engine immediately, so it needs psycopg2 — tests and `run_test_bot` swap in sqlite. Tests build that sqlite database with `wd_db.testing.sqlite_engine()` and store rows with `seed(engine, *rows)`.
- **API reference:** [wd_db](../docs/reference/wd-db.md) · [extension](../docs/reference/wd-db.extension.md) · [errors](../docs/reference/wd-db.errors.md) · [extras](../docs/reference/wd-db.extras.md)
