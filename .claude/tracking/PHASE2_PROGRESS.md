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

## Tasks (not yet started — plan not yet executed)

- [ ] 1. wd-discord/src/wd_discord/interactions.py — `ApplicationCommandOptionType`, fix `CommandOption.field_type`
- [ ] 2. wd-discord/src/wd_discord/interactions.py — pydantic `CommandOption` + `RegisteredCommand`
- [ ] 3. wd-discord/src/wd_discord/embed.py (new) — minimal `Embed`/`EmbedField`
- [ ] 4. wd-discord/src/wd_discord/gateway/events.py — `Interaction` model, wire `EventName.INTERACTION_CREATE`, regenerate `dispatch.pyi`
- [ ] 5. wd-discord/src/wd_discord/client.py — `Client._get_application_id` (lazy fetch + cache + write-back)
- [ ] 6. wd-discord/src/wd_discord/client.py — `create_interaction_response` + global command CRUD
- [ ] 7. wd-bot/src/wd_bot/signature.py (new) — `command_signature`; drop `AutoSync.get_signature`
- [ ] 8. wd-bot/src/wd_bot/auto_sync.py — `CommandRecord`/`GlobalSyncedCommand`/`GuildSyncedCommand` + diff engine
- [ ] 9. wd-bot/src/wd_bot/commands.py (new) — `Command`
- [ ] 10. wd-bot/src/wd_bot/cogs.py — `Cog.command()` decorator
- [ ] 11. wd-bot/src/wd_bot/bot.py — `_commands` registry, `INTERACTION_CREATE` dispatch, `sync_commands`
- [ ] 12. src/winter_dragon/cogs/percentage.py (new) — `/percentage` command; `Snowflake.__int__`
- [ ] 13. src/winter_dragon/cogs/bot_commands.py (new) — admin `/bot-commands-list` / `/bot-commands-resync`
- [ ] 14. Full-suite verification, lint/type-check, manual smoke test via `run-wd-discord`

## Notes / deviations from plan

(none yet — plan not yet executed)

## Deferred (not part of this phase)

Guild-scoped commands. Mechanics already decided (see the spec's "Deferred: guild scoping"
section and the `app-commands-guild-scoping-todo` project memory); the open question is purely
*when/how a command author should choose* guild scoping. `GuildSyncedCommand` + its diff function
are built in Task 8 but unreachable — `Cog.command()` gets no `guild_ids` parameter in this phase.
