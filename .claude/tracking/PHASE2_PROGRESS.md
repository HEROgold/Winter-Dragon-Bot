# Phase 2 Progress Tracker

Tracks execution of
[docs/superpowers/plans/2026-09-14-app-commands-implementation.md](../../docs/superpowers/plans/2026-09-14-app-commands-implementation.md)
(see [PHASE2_PLAN.md](PHASE2_PLAN.md) for the short summary + links). Update this file right
before each `git commit` so work-in-progress state survives context loss/compaction. Mark items
`[x]` only once done and verified (tests pass for that piece), not just written.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

## Design + planning

- [x] Spec written, grilled, and committed: `docs/superpowers/specs/2026-09-14-app-commands-design.md`
- [x] Implementation plan written and committed: `docs/superpowers/plans/2026-09-14-app-commands-implementation.md`
- [x] Merged `extensions-package-moduletype` into `v2` (prerequisite: touches `wd_bot/bot.py`, which this phase also modifies)

## Tasks

- [x] 1. wd-discord/src/wd_discord/interactions.py — `ApplicationCommandOptionType`, fix `CommandOption.field_type`
- [x] 2. wd-discord/src/wd_discord/interactions.py — pydantic `CommandOption` + `RegisteredCommand`
- [x] 3. wd-discord/src/wd_discord/embed.py (new) — minimal `Embed`/`EmbedField`
- [x] 4. wd-discord/src/wd_discord/gateway/events.py — `Interaction` model, wire `EventName.INTERACTION_CREATE`, regenerate `dispatch.pyi`
- [x] 5. wd-discord/src/wd_discord/client.py — `Client._get_application_id` (lazy fetch + cache + write-back)
- [x] 6. wd-discord/src/wd_discord/client.py — `create_interaction_response` + global command CRUD
- [x] 7. wd-bot/src/wd_bot/signature.py (new) — `command_signature`; drop `AutoSync.get_signature`
- [~] 8. wd-bot/src/wd_bot/auto_sync.py — `CommandRecord`/`GlobalSyncedCommand`/`GuildSyncedCommand` + diff engine
- [ ] 9. wd-bot/src/wd_bot/commands.py (new) — `Command`
- [ ] 10. wd-bot/src/wd_bot/cogs.py — `Cog.command()` decorator
- [ ] 11. wd-bot/src/wd_bot/bot.py — `_commands` registry, `INTERACTION_CREATE` dispatch, `sync_commands`
- [ ] 12. src/winter_dragon/cogs/percentage.py (new) — `/percentage` command; `Snowflake.__int__`
- [ ] 13. src/winter_dragon/cogs/bot_commands.py (new) — admin `/bot-commands-list` / `/bot-commands-resync`
- [ ] 14. Full-suite verification, lint/type-check, manual smoke test via `run-wd-discord`

## Notes / deviations from plan

- Task 5 also fixed `wd-config/src/wd_config/bot.py`. `Settings.application_id = Config[int | None](None)`
  raised `ValueError` on any configured int. It is now `Config[int | None](0, optional=True)`, the
  pattern confkit's docs give for optional values. `0` is falsy, so existing truthy checks still work.
- Task 5's test works around a pre-existing pydantic/lazy-import schema bug when building
  `Guild`/`Application` (pre-touch imports of `Snowflake` and `VerificationLevel`). Not fixed here.
- Task 7's test file omits `from __future__ import annotations`, because the future import makes
  `inspect.signature` render quoted annotations. Command modules that use the future import get
  quoted signatures. Those are still stable, so drift detection works.
- `uvx ruff format --check .` already fails on 105 files repo-wide. New and touched files in this
  phase are held to it; the rest is pre-existing debt.
- Task 8 found wd-db missing runtime deps (psycopg2, h2 for `httpxyz` http2, httpxyz, herogold).
  Added with `uv add --package wd-db`: psycopg2-binary, httpxyz[http2], herogold.

## Deferred (not part of this phase)

Guild-scoped commands. Mechanics already decided (see the spec's "Deferred: guild scoping"
section and the `app-commands-guild-scoping-todo` project memory); the open question is purely
*when/how a command author should choose* guild scoping. `GuildSyncedCommand` + its diff function
are built in Task 8 but unreachable — `Cog.command()` gets no `guild_ids` parameter in this phase.
