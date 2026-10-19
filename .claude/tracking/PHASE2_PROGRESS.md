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
- [x] 8. wd-bot/src/wd_bot/auto_sync.py — `CommandRecord`/`GlobalSyncedCommand`/`GuildSyncedCommand` + diff engine
- [x] 9. wd-bot/src/wd_bot/commands.py (new) — `Command`
- [x] 10. wd-bot/src/wd_bot/cogs.py — `Cog.command()` decorator
- [x] 11. wd-bot/src/wd_bot/bot.py — `_commands` registry, `INTERACTION_CREATE` dispatch, `sync_commands`
- [x] 12. src/winter_dragon/cogs/percentage.py (new) — `/percentage` command; `Snowflake.__int__`
- [x] 13. src/winter_dragon/cogs/bot_commands.py (new) — admin `/bot-commands list|resync` group
- [x] 14. Verification done: 196 passed, only the 5 baseline failures. Live smoke test on 2026-10-03 with a file-backed sqlite DB: the first run created the commands, a second run made no command calls, and the GroupCog switch created `/bot-commands` and deleted the flat commands (204). A later run again made no calls. An invocation of `/percentage` with a user option at 13:53 was answered (callback 204).

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
- Task 9: `Command` resolves only option-parameter annotations (via ForwardRef, reifying `lazy from`
  proxies), so `self`/`interaction` types may stay under TYPE_CHECKING. Option types like `User`
  must be imported at module level in cog modules.
- Task 11: the plan's `Bot.sync_commands` body moved out of Bot. `wd_bot.auto_sync` has a
  `CommandSyncer` Protocol and `DefaultCommandSyncer(engine=None)`, and `Bot.syncer` is a get/set
  property (user direction). `Bot.sync_commands(client)` is a thin delegate.
- Task 11: `Bot.client` attribute added (the plan's cogs used `self.bot.client`, which didn't exist).
  `_init_cogs` awaits `auto_load()`, so commands are registered before the startup sync. Deletes
  are skipped when any extension failed to load, so a broken cog doesn't delete its live commands.
- Logging: herogold 4.0.0 renders t-strings, so log calls use `t"..."`, not %-style.
- Task 12: `/percentage` reproduces the legacy love_meter embed (title "Love Meter", 0xFF0000, one
  inline field), seeded by the sum of both user IDs.
- Task 13: `default_member_permissions` is threaded through Command, `Cog.command`, the payload, the
  client and the syncer. `Command.signature()` covers handler signature + description + permissions,
  so description or permission changes sync too. Bot has a public `commands` property.
- Final-review fixes: the syncer creates its own tables on first sync, and a failed startup sync is
  logged instead of stopping the bot. `default_member_permissions` is always sent (null clears it).
  The admin commands refuse outside a guild. An edit that 404s falls through to create, and a delete
  that 404s counts as done. `sync` holds an asyncio.Lock. An empty registry never mass-deletes.
  A handler that raises gets an ephemeral error reply. The Interaction and RegisteredCommand fields
  Discord always sends are now declared, so they no longer show up as unknown fields.
- Final-review minors: signatures render annotations with `Format.STRING`, which means one more
  edit per command on the first deploy. `invoke` skips undeclared options with a warning.
  Duplicate command names across cogs log a warning. herogold is pinned `>=4.0.0` in wd-bot, wd-db
  and wd-discord.
- #8 done: `GroupCog` registers one `CommandGroup` (`/bot-commands list|resync`), configured with
  class kwargs `name=`, `description=` and `default_member_permissions=`. Only the group carries permissions.
- The smoke test found two bugs, both fixed. `Snowflake.__str__` returned the repr, so stored command IDs
  and the interaction callback URL were invalid. The sqlite-only BigInteger primary key doesn't autoincrement,
  which affects tests and drivers, not Postgres.
- Open for the user: scoping the sync-tracking rows by `application_id` (until then a dev bot and the
  prod bot must not share a DB).

## Deferred (not part of this phase)

Guild-scoped commands. Mechanics already decided (see the spec's "Deferred: guild scoping"
section and the `app-commands-guild-scoping-todo` project memory); the open question is purely
*when/how a command author should choose* guild scoping. `GuildSyncedCommand` + its diff function
are built in Task 8 but unreachable — `Cog.command()` gets no `guild_ids` parameter in this phase.
