# wd-db

Database access on SQLModel/SQLAlchemy: the process-wide `engine`/`session` (built from `DbUrl` config), `SessionMixin`, and the model bases.

- **Depends on:** wd-config (plus sqlmodel, sqlalchemy, psycopg, herogold).
- **Start here:** `wd_db.extension.model` — `BaseModel` is a repository (`add/update/get/get_all/delete/fetch`) that auto-registers every subclass; `SQLModel` and `DiscordID` are the bases tables use. `wd_db.constants` holds `DATABASE_URL`, `engine`, `session`.
- **Gotcha:** importing `wd_db.constants` creates a Postgres engine immediately, so it needs psycopg2 — tests and `run_test_bot` swap in sqlite.
- **API reference:** [wd_db](../docs/reference/wd-db.md) · [extension](../docs/reference/wd-db.extension.md) · [errors](../docs/reference/wd-db.errors.md) · [extras](../docs/reference/wd-db.extras.md)
