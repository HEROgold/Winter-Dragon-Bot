# Discord application-command (slash command) support — design

## Goal

Introduce a general application-command framework so cogs can define chat-input
("slash") commands, with:

- automatic, diff-based sync to Discord (global + per-guild) that avoids
  unnecessary API calls,
- a first concrete command: given a mentionable user, compute a random 0-100%
  "compatibility" seeded by both users' IDs (`winter_dragon/cogs`),
- a built-in admin command to inspect/force the sync state (`list`, `resync`).

This closes a real gap: the current `wd_bot.cogs.Cog` framework explicitly has
**no** command-registration or `INTERACTION_CREATE` dispatch yet
(`Cog.load()`'s docstring: "there's no CommandTree yet to sync app commands
against"; `GroupCog` is marked "future app-command-group cogs (Phase 2)").
`AutoSync`/`SyncedCommand` already exist in `wd_bot` but are unused — this
design is what wires them up.

## Non-goals

- Subcommand groups beyond the one needed for the admin command.
- Autocomplete, choices, min/max constraints, or option types other than
  STRING/INTEGER/BOOLEAN/USER/CHANNEL/ROLE/NUMBER (only USER is exercised by
  the concrete command; the others are modeled for completeness of the
  option-type mapping, not exhaustively tested).
- Custom per-guild command enable/disable — Discord's own guild Integrations
  page already covers this; duplicating it would be redundant surface area.
- Migrating the legacy `wd_cogs` (discord.py-based) app commands. That package
  is a separate, pre-existing migration concern.

## Architecture

### 1. `wd_discord` — data model + REST

- **`Interaction` (`DiscordModel`)**: parses an `INTERACTION_CREATE` payload
  (`id`, `application_id`, `type`, `data` [command `id`/`name`/`type`/
  `options`/`resolved`], `guild_id`, `channel_id`, `member`, `user`, `token`,
  `version`). Wired into `EventName.INTERACTION_CREATE` the same way
  `MESSAGE_CREATE` already resolves to `Message`.
- **`ApplicationCommandOptionType` (new `IntEnum`)**: the option-type enum
  Discord actually defines (SUB_COMMAND=1, SUB_COMMAND_GROUP=2, STRING=3,
  INTEGER=4, BOOLEAN=5, USER=6, CHANNEL=7, ROLE=8, MENTIONABLE=9, NUMBER=10,
  ATTACHMENT=11). `CommandOption.field_type` in `interactions.py` currently
  (incorrectly) types itself as `ApplicationCommandType` — the *command*
  type — instead of this. Fixed as part of this work.
- **`ApplicationCommand`/`CommandOption`/etc. become real `DiscordModel`s**
  (pydantic), replacing the current hand-validated `@dataclass` forms in
  `interactions.py` — already flagged as a TODO in `gateway/events.py`
  ("fix that alongside the Interaction/CommandTree pydantic port").
- **New `Client` REST methods**: `create_interaction_response` (POST
  `/interactions/{id}/{token}/callback`, type 4 `CHANNEL_MESSAGE_WITH_SOURCE`);
  per-scope CRUD — `create_global_command` / `edit_global_command` /
  `delete_global_command` / `get_global_commands`, and the guild-scoped
  equivalents. Individual CRUD, deliberately **not** the bulk-overwrite
  endpoint — bulk PUT replaces the entire command set on every call, which
  conflicts with "don't do unnecessary work" and this design's diff-then-patch
  approach.

### 2. `wd_bot.signature` (new module)

`command_signature(func: Callable[..., object]) -> str` — a standalone,
side-effect-free function returning a stable string form of a callable's
signature (`str(inspect.signature(func))`), used to detect when a command's
definition has changed. Both `Command` and `AutoSync` depend on this function;
neither depends on the other for it. `AutoSync.get_signature` is removed in
favor of this.

A TODO comment on this module points at
[HEROgold/HeroPy#33](https://github.com/HEROgold/HeroPy/issues/33), tracking
upstreaming an equivalent into `herogold` (it's generic enough — signature-
drift detection isn't Discord-specific) so wd-bot can eventually depend on
herogold's version instead of keeping a local copy.

### 3. `wd_bot.commands.Command` (new class)

Built by the `Cog.command(name, description)` decorator (sibling to the
existing `Cog.listener`), wrapping the decorated method and encapsulating the
whole unit of work for one command:

- `name`, `description`
- `options: list[CommandOption]` — derived from the wrapped function's
  type-annotated parameters (skipping `self`/`interaction`) via a type→option
  mapping (e.g. a `User` parameter → a `USER` option)
- `to_application_command() -> ChatInputApplicationCommand` — builds the
  registration payload
- `signature() -> str` — via `wd_bot.signature.command_signature`, fed into
  the sync diff
- `invoke(cog: Cog, interaction: Interaction) -> None` — resolves each raw
  interaction option (using `interaction.data.resolved` for USER options, not
  just the raw snowflake) into kwargs matching the handler's parameter names,
  then calls the wrapped function bound to `cog`; catches and logs handler
  exceptions, sending an ephemeral error response instead of leaving Discord's
  "thinking…" state hanging
- `__get__` descriptor so a `Command` still behaves sanely if ever accessed as
  a plain attribute on a `Cog` instance

`Cog.command(...)` itself is a thin decorator: it builds and returns a
`Command(func, name=..., description=...)`.

### 4. `wd_bot.bot.Bot`

- `_commands: dict[tuple[int | None, str], tuple[Cog, Command]]` registry
  (guild_id-or-None, name) → (owning cog instance, `Command`), built at
  cog-load time (mirrors the existing `_listeners` dict building).
- An `INTERACTION_CREATE` listener (registered like any other gateway
  listener) that looks up the invoked command by `(guild_id, name)` falling
  back to `(None, name)` for global, and calls `command.invoke(cog,
  interaction)`.
- A startup sync step (see below) run once cogs are loaded, before/alongside
  gateway connect.

### 5. Sync engine (fleshes out existing `AutoSync`/`SyncedCommand`)

For each scope — global, and each guild with guild-scoped commands — and for
every `Command` currently registered in that scope:

1. Compute `command.signature()`.
2. Compare against the stored `SyncedCommand` row for
   `(command_name, scope)`.
3. **No row / signature differs** → create or edit via the individual REST
   call, then upsert the `SyncedCommand` row with the new signature.
4. **Row exists with no matching registered command** (command was removed
   from code) → delete via REST, then delete the row.
5. **Signature matches** → no REST call at all.

This guarantees only actually-changed commands touch the Discord API,
directly satisfying "keep commands in sync without overwhelming Discord's
limits and without unnecessary work."

## Concrete command: `winter_dragon/cogs/percentage.py`

```
@Cog.command(name="percentage", description="Calculate a random compatibility percentage with another user")
async def percentage(self, interaction: Interaction, user: User) -> None:
    ...
```

- Single `USER` option.
- Seeds a **local** `random.Random(interaction_user.id + user.id)` instance
  (not the legacy `wd_cogs/games/love_meter.py` pattern of calling the global
  `random.seed(...)`, which leaks global RNG state) and sends back
  `rng.randint(0, 100)` via `create_interaction_response`.

## Admin management command

A `GroupCog` (`/bot-commands`) with:

- `list` — every registered `Command` plus its synced/pending state, by
  comparing the live registry against `SyncedCommand` rows (no REST call).
- `resync` — forces the diff-and-push sync immediately for the invoking
  guild (and global, if the invoker has appropriate permissions).

## Error handling

Consistent with the repo's "errors as values" convention: `Client` REST calls
return `NetworkError` on failure rather than raising. The sync engine treats a
failed create/edit/delete as "not yet synced" and leaves the `SyncedCommand`
row untouched, so it's retried on the next sync pass rather than being
incorrectly marked done. `Command.invoke` catches and logs handler exceptions
and always sends *some* interaction response so Discord doesn't show a
timed-out interaction to the user.

## Testing

All offline / unit-level:

- `command_signature` — pure function, trivial cases.
- `Command` option derivation (type → `ApplicationCommandOptionType` mapping)
  and interaction-option resolution (including the `resolved.users` lookup
  for `USER` options).
- Sync diff logic — given fake `SyncedCommand` rows and a fake command
  registry, assert exactly the expected create/edit/delete set (and no calls
  when signatures match).
- `Interaction` parsing — a `parse_dispatch`-overload-style test, matching the
  existing `MESSAGE_CREATE`/`GUILD_CREATE` pattern.

Real end-to-end registration/interaction handling against Discord isn't
unit-testable; verify manually via the `run-wd-discord` skill against a test
guild before considering this done.
