---
name: architecture
description: WinterDragonV2 package layering, coupling rules, dependency injection, service locators, registries, domain-logic placement, and DRY. Use when creating modules or packages, adding dependencies between wd-* packages, wiring collaborators (bot/session/handlers), deciding where domain logic lives, or extracting shared code.
---

# Architecture — layering, DI & domain placement

Per-package public API: [docs/reference/index.md](../../../docs/reference/index.md). Read the page, not the source, to find a symbol.

## The layer diagram (dependency direction is law)

```
wd-types            wd-config             ← leafs: depend on nothing internal
                    /       \
                wd-db      wd-discord     ← infrastructure (each: wd-config only)
                   \       /    \
                    \  wd-core  wd-errors ← shared domain helpers / error machinery (on wd-discord)
                     \    |     /
                       wd-bot             ← bot framework: Bot, Cog/GroupCog, commands, components, sync
                          |
                    winter_dragon         ← the app (root src/): __main__ + the live cogs
```

- **The live feature code is `src/winter_dragon/cogs/`.** `python -m winter_dragon` builds `Bot(extensions_package=cogs)` from there. Its tests live in `wd-bot/tests/` (`test_steam_*`, `test_fuel_cog`, ...).
- **`wd-cogs` is a legacy catalog** of discord.py-era cogs (`discord.Interaction`, `app_commands`); discord.py isn't installed and the app never loads it. Port a cog into `winter_dragon/cogs/` on the `wd_bot` API rather than editing it in place. (`Bot`'s default `extensions_package` is still `wd_cogs` — always pass one.)
- **wd-discord never imports wd-core/wd-db/wd-bot.** It is the transport: HTTP (`Client`, transport only) plus stores and client-bound entities ([entities/](../../../wd-discord/src/wd_discord/entities/)), WebSocket ([gateway/](../../../wd-discord/src/wd_discord/gateway/)), errors-as-values. Responses are validated `DiscordModel`s (see [discord-api-models](../discord-api-models/SKILL.md)); outbound bodies are built without a socket so they test offline — plain functions/dataclasses (`build_presence`, `GatewayActivity.to_dict` in [gateway/connection.py](../../../wd-discord/src/wd_discord/gateway/connection.py)) or a pydantic `BaseModel` when Discord documents limits worth validating (`ApplicationCommandParams` in [interactions.py](../../../wd-discord/src/wd_discord/interactions.py)). Its only internal dep is `wd-config`.
- **wd-bot is framework, not features.** Lifecycle, extension discovery ([extensions.py](../../../wd-bot/src/wd_bot/extensions.py)), dispatch, command sync. A new feature is a cog in `winter_dragon/cogs/`; a reusable mechanism goes in `wd_bot` or `wd_core`.
- **Declare every internal dep in the package's `pyproject.toml`** via `uv add --package <member> wd-x` (see [dependencies](../dependencies/SKILL.md)). Known debt: `wd-bot` imports `wd_db`, and `wd-errors` imports `wd_discord`, without declaring them.
- Cross-package structural types go in **wd-types** (`Mentionable`, `alias.py`); shared error machinery in **wd-errors**.

## Dependency injection — the three sanctioned forms

1. **Constructor injection** (default). Collaborators are parameters: `AuditEventHandler(event, session, bot)` ([wd_core/events.py](../../../wd-core/src/wd_core/events.py)); `SteamSaleNotifier` takes its client and store as dataclass fields. Cogs take `**kwargs: Unpack[BotArgs]` — `bot` `Required`, `db_session` `NotRequired` with a fallback in `Cog.__init__` ([wd_bot/cogs.py](../../../wd-bot/src/wd_bot/cogs.py)): `kwargs.get("db_session", Session(engine))`. Tests inject; runtime falls back to the shared default.

2. **Self-registering factory registries** — an open set of handlers keyed by a value. A factory class holds a `ClassVar` dict + `register()`/`get_*()` classmethods, populated by `__init_subclass__` on a base, so defining a subclass IS the registration:
   - `ErrorFactory` ([wd_errors/factory.py](../../../wd-errors/src/wd_errors/factory.py)), registered from `DiscordError.__init_subclass__` ([error.py](../../../wd-errors/src/wd_errors/error.py)).
   - `AuditEventFactory`, keyed by the subclass kwarg: `class X(AuditEvent, action=AuditLogAction.ban)` ([wd_core/events.py](../../../wd-core/src/wd_core/events.py)).
   - `BaseModel.__init_subclass__` auto-collects every model ([wd_db/extension/model.py](../../../wd-db/src/wd_db/extension/model.py)).
   Registration happens at import time — a package `__init__` must import the modules holding the subclasses.

3. **Service locator (module singletons)** — only for process-wide resources: `engine`/`session` in [wd_db/constants.py](../../../wd-db/src/wd_db/constants.py) (via `SessionMixin`) and the static config classes (`Settings`, `DbUrl`). Anything a constructor parameter can carry doesn't get a new singleton.

Decorator injection for config values: `@Config.with_kwarg("Tokens", "discord_token")` (see config-and-constants).

## Avoiding repetition — the reuse toolbox, in order

1. **Import it.** If two packages need it, move it down a layer (usually wd-types/wd-core), don't copy. In-tree anti-examples: `Region`/`Platform` in both `riot_clash_api.py` and `league_of_legends.py`; `Cassiopeia*` protocols in two cogs.
2. **Mixins** for orthogonal capabilities: `LoggerMixin` (herogold) gives `self.logger`; `SessionMixin` shares the DB session.
3. **Base classes with behavior**: `BaseModel` is a repository (`add/update/get/get_all/delete/fetch`); `Cog`/`GroupCog` configure per-subclass `CogFlags` through `__init_subclass__`.
4. **Decorators** for cross-cutting policy: `returns_known_exception`, `with_known_exception`, `@loop`, `@Config.with_kwarg`.
5. **Descriptors/Protocols** — see advanced-patterns.
