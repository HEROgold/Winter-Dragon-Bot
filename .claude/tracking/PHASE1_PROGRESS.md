# Phase 1 Progress Tracker

Tracks execution of [PHASE1_PLAN.md](PHASE1_PLAN.md). Update this file right before each `git commit`
so work-in-progress state survives context loss/compaction. Mark items `[x]` only once done and verified
(imports/tests pass for that piece), not just written.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

## Changes

- [x] 1. wd-discord/src/wd_discord/client.py — delete `BotUser`, fix `get_shard_manager` (intents param, no `async with`)
- [x] 2. wd-discord/src/wd_discord/permissions.py — add `Permissions.all()` / `.none()`
- [x] 3. wd-core/src/wd_core/constants.py — import `Permissions`, fix `BOT_PERMISSIONS`
- [x] 4. wd-discord/src/wd_discord/gateway/connection.py — fix `Ready` model + `parse_ready`; add `Gateway.listen()`
- [x] 5. wd-discord/src/wd_discord/gateway/events.py (new) — `RawEvent`, `GuildCreate`, `Message`, `parse_dispatch`; wire into `gateway/__init__.py` + `wd_discord/__init__.py`
- [x] 6. wd-discord/src/wd_discord/gateway/sharding.py — `ShardManager.serve_forever()`
- [x] 7. wd-bot/src/wd_bot/cogs.py — rewrite `Cog`/`GroupCog` (wd-native, `@Cog.listener()`, drop discord.py deps)
- [x] 8. wd-bot/src/wd_bot/bot.py — rewrite `Bot` (drop prefix/help_command/tree_cls, cog registry, dispatcher, forever `start()`, new `get_bot_invite`)
- [x] 9. wd-bot/pyproject.toml — `uv add wd-discord wd-core wd-errors wd-types` (also uncommented `wd-bot/tests` in root pyproject.toml's pytest `testpaths`)
- [x] 10. Tests — `wd-bot/tests/fixtures/example_cog.py`, `wd-bot/tests/test_bot.py` (add_cog/dispatch/module-spec loading), gateway dispatch unit tests, `Permissions.all()` cases. NOT done: optional live smoke test (needs a real bot token; skipped for now, not required by the plan's completion criteria)

## Verification (run after changes above are done)

- [x] `uv sync` (needed `uv sync --all-packages` once, to pull in wd-discord's `dev` dependency-group (pytest/pytest-asyncio) which the root venv didn't have)
- [x] `uv run pytest wd-discord/tests wd-bot/tests` — 75 passed, 5 failed (all pre-existing/unrelated, see baseline note below), 10 skipped, 1 xfailed
- [x] Lint (`ruff check`) and format (`ruff format --check`) clean on every touched production file (a few pre-existing, unrelated violations on lines I didn't touch were left alone: an E501 TODO line in `client.py`, a TD003/FIX002 TODO in `permissions.py`, pervasive S101/D103/PLR2004 findings across the whole pre-existing `wd-discord/tests` test-file style)
- [x] `python -c "from wd_bot.bot import Bot"` succeeds (verified via `uv run python -c "from wd_bot.bot import Bot; Bot()"`)
- [ ] Live smoke test confirms bot stays connected (optional, needs real token — not run)

## Notes / deviations from plan

- **Systemic bug found while implementing item 4/5**: `DiscordModel` subclasses across wd_discord that reference
  another lazily-imported (`lazy from X import Y`) class as a field's raw type (e.g. `user: User`) fail
  `PydanticSchemaGenerationError` at class-definition time if that target class hasn't been forced/resolved yet
  elsewhere in the process — pydantic sees the unresolved `<lazy_import ...>` proxy, not the real class. Confirmed
  this is **pre-existing and already present** in `application/team.py`, `application/application.py`,
  `guild/emoji.py`, `guild/sticker.py`, `channel/channel.py`, `guild/guild.py` — it's simply never triggered today
  because nothing forces those lazy imports during the current test run. Fixing it repo-wide is out of scope for
  Phase 1. Local fix applied only to files this plan touches: `connection.py`'s `Ready.user` and the new
  `events.py`'s `User`/`Snowflake` imports are eager (`from X import Y`, not `lazy from`), and `GuildCreate` does
  **not** subclass `Guild` (which is itself currently broken this same way) — it's a standalone `DiscordModel` with
  its own minimal field set. Left a TODO(Phase 2) in `events.py` pointing at this.
- Also fixed while touching these files: `Ready`/`connection.py`/`sharding.py`/new `client.py` code referenced
  `Intents` as a type annotation with no import anywhere (pre-existing, same failure mode as above but harmless at
  runtime since annotations are strings). Added `TYPE_CHECKING`-only imports of `wd_core.intents.Intents` — avoids
  a real runtime circular import (wd_core depends on wd_discord, not the reverse) while fixing static analysis.
- Updated 2 pre-existing tests in `test_gateway_payload.py` (`test_parse_ready_with_dispatch_wrapper`,
  `test_parse_ready_accepts_inner_dict`) to pass a valid `user` payload, since `Ready.user` is now a required real
  `User` instead of an optional raw dict — intentional per the plan.
- Ran `uv sync --all-packages` to get `pytest`/`pytest-asyncio` installed (the root venv didn't have them; they're
  declared in `wd-discord/pyproject.toml`'s `dev` dependency-group, not the root).
- Baseline before any Phase 1 changes (clean `git stash -u`): 8 failed, 61 passed, 10 skipped, 1 xfailed on
  `uv run pytest -q --ignore=wd-discord/tests/test_rate_limit.py --ignore=wd-discord/tests/test_errors.py
  --ignore=wd-discord/tests/test_gateway.py`. After items 1-6 + their tests: 5 failed (all pre-existing, unrelated:
  `test_shard_for_guild_routes_after_start` + 4 `test_utils.py` XOR/descriptor tests), 72 passed, 10 skipped, 1
  xfailed. After items 7-10 (full Phase 1): same 5 pre-existing failures, 75 passed.
- `get_bot_invite()` hits a separate pre-existing bug in `wd_config`: `Settings.application_id = Config[int
  \| None](None)` — confkit infers the descriptor's data type from the *default* value, so a `None` default locks
  it to a null-only converter, and it can't parse the real snowflake int already stored in this dev machine's
  `config.ini`. Unrelated to wd-bot/wd-discord/wd-core (this plan's scope) — not fixed here. `Bot()` construction
  and `get_bot_invite()`'s own logic are otherwise correct; this only surfaces when `Settings.application_id` is
  actually read with a real configured value.
- `Cog.__init__`'s fallback `Session(engine)` (when no `db_session` kwarg is given) uses `wd_db.constants.engine`,
  which eagerly `create_engine()`s a real Postgres connection at import time and needs `psycopg2` — not installed
  in this dev environment (pre-existing gap, unrelated to this change). `wd-bot/tests/test_bot.py` works around it
  with an autouse fixture that installs a `sys.modules["wd_db.constants"]` stub (sqlite-backed `engine`) before any
  `Cog` is constructed, since the target of the lazy import is resolved from `sys.modules` first.
- Uncommented `"wd-bot/tests"` in the root `pyproject.toml`'s `[tool.pytest.ini_options] testpaths` (was already
  present, commented out, inviting exactly this once a package gains tests).
