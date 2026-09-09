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
- [ ] 7. wd-bot/src/wd_bot/cogs.py — rewrite `Cog`/`GroupCog` (wd-native, `@Cog.listener()`, drop discord.py deps)
- [ ] 8. wd-bot/src/wd_bot/bot.py — rewrite `Bot` (drop prefix/help_command/tree_cls, cog registry, dispatcher, forever `start()`, new `get_bot_invite`)
- [ ] 9. wd-bot/pyproject.toml — `uv add wd-discord wd-core wd-errors wd-types`
- [~] 10. Tests — gateway dispatch unit tests (done: `test_gateway_dispatch.py`, `Permissions.all()` cases added) / still TODO: `wd-bot/tests/fixtures/example_cog.py`, optional live smoke test

## Verification (run after changes above are done)

- [ ] `uv sync`
- [ ] `uv run pytest wd-discord/tests wd-bot/tests` green
- [ ] Lint/type-check touched files clean
- [ ] `python -c "from wd_bot.bot import Bot"` succeeds
- [ ] Live smoke test confirms bot stays connected (optional, needs real token)

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
  xfailed.
