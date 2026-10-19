# Application-command (slash command) support (Phase 2 of 2)

## Context

`.claude/tracking/PHASE1_PLAN.md`/`PHASE1_PROGRESS.md` explicitly deferred all of this: "no
`Interaction` model, no interaction-response REST, no slash-command registration/dispatch (all
Phase 2)." Phase 1 made `Bot` a genuinely forever-running, event-dispatching gateway client;
Phase 2 adds the ability to define, register, sync, and dispatch chat-input application commands
on top of it.

Full design rationale (including grilled-out decisions — global-only v1, the split
`CommandRecord`/`GlobalSyncedCommand`/`GuildSyncedCommand` schema, the minimal `Embed` model, the
deferred guild-scoping policy) lives in
[docs/superpowers/specs/2026-09-14-app-commands-design.md](../../docs/superpowers/specs/2026-09-14-app-commands-design.md).
The full task-by-task implementation plan (14 tasks, TDD steps, exact file paths and code) lives in
[docs/superpowers/plans/2026-09-14-app-commands-implementation.md](../../docs/superpowers/plans/2026-09-14-app-commands-implementation.md).
This file is a short pointer, not a duplicate — see those two documents for everything else.

## Shipped in this phase

- `wd_discord`: `Interaction`/`InteractionData`/`ResolvedData` models wired into
  `EventName.INTERACTION_CREATE`; pydantic `CommandOption` + `RegisteredCommand`;
  `ApplicationCommandOptionType`; a minimal `Embed`; `Client` REST methods for interaction
  responses and global command CRUD; `Snowflake.__int__`.
- `wd_bot`: `command_signature` (standalone, with a TODO tracking upstreaming into `herogold` at
  [HEROgold/HeroPy#33](https://github.com/HEROgold/HeroPy/issues/33)); `CommandRecord` +
  `GlobalSyncedCommand` + `GuildSyncedCommand` (built, guild table unreachable in v1) + diff
  functions; `Command` (encapsulates one command's definition + dispatch); `Cog.command()`;
  `Bot._commands` registry, `INTERACTION_CREATE` dispatch, `Bot.sync_commands()`.
- `winter_dragon/cogs`: `/percentage` (the requested mentionable-user, seeded-random-% command)
  and an admin `/bot-commands-list` / `/bot-commands-resync` pair.

## Explicitly deferred (tracked separately)

Guild-scoped commands — see the "Deferred: guild scoping" section of the design spec above for
what's already decided vs. still open when this gets picked back up (also recorded as an
`app-commands-guild-scoping-todo` entry in Claude's cross-session project memory).
