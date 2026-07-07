---
name: architecture
description: WinterDragonV2 package layering, coupling rules, dependency injection, service locators, registries, domain-logic placement, and DRY. Use when creating modules or packages, adding dependencies between wd-* packages, wiring collaborators (bot/session/handlers), deciding where domain logic lives, or extracting shared code.
---

# Architecture — layering, DI & domain placement

## The layer diagram (dependency direction is law)

```
wd-types   wd-errors   wd-config      ← leaves: depend on nothing internal
     \         |        /   \
      \        |    wd-db   wd-discord   ← infrastructure (each: wd-config only)
       \       |       \     /
        \      |       wd-core           ← domain (config + discord)
         \     |      /
           wd-cogs                       ← features (core + db + discord)
              |
           wd-bot                        ← composition/runtime
```

Rules:

- **wd-discord never imports wd-core/wd-db.** It is a thin transport layer: HTTP (`Client` in [client.py](../../../wd-discord/src/wd_discord/client.py)) and WebSocket ([gateway/](../../../wd-discord/src/wd_discord/gateway/)), errors-as-values, pure dataclasses with `to_dict()`/`parse_*` functions factored out so they test without a socket ([gateway/connection.py](../../../wd-discord/src/wd_discord/gateway/connection.py): `build_presence`, `parse_ready`).
- **Domain logic lives in wd-core and wd-cogs** — e.g. audit-log behavior (`AuditEvent`, `create_embed`) in [wd-core/src/wd_core/events.py](../../../wd-core/src/wd_core/events.py); feature behavior in `wd-cogs`.
- **wd-bot only composes**: cog discovery via `pkgutil` ([bot.py](../../../wd-bot/src/wd_bot/bot.py)), lifecycle, reload. New behavior goes in a cog or in core, not in `wd_bot`.
- **Declare every internal dep in the package's `pyproject.toml`** as `{ workspace = true }`. Known debt: `wd-bot` imports `wd_db`/`wd_errors`/`wd_core`/`wd_cogs` but declares only `wd-config` — it works only because the workspace installs everything. Don't add more undeclared imports; declare them when touching a manifest.
- Cross-package structural types go in **wd-types** (`Mentionable` protocol, `alias.py`); shared error machinery in **wd-errors**.

## Dependency injection — the three sanctioned forms

1. **Constructor injection** (default). Collaborators are parameters: `AuditEventHandler(event, session, bot)` ([events.py](../../../wd-core/src/wd_core/events.py)). Cogs take `**kwargs: Unpack[BotArgs]` where `bot` is `Required` and `db_session` is `NotRequired` with a fallback: `self.session = kwargs.get("db_session", Session(engine))` ([wd-bot/src/wd_bot/cogs.py:60](../../../wd-bot/src/wd_bot/cogs.py#L60)). Tests inject; runtime falls back to the shared default.

2. **Self-registering factory registries** — for open sets of handlers keyed by a value. The pattern: a factory class holding a `ClassVar` dict + `register()`/`get_*()` classmethods, populated by `__init_subclass__` on a base class, so defining a subclass IS the registration:
   - `ErrorFactory` ([wd-errors/src/wd_errors/factory.py](../../../wd-errors/src/wd_errors/factory.py)), registered from [error.py](../../../wd-errors/src/wd_errors/error.py) `__init_subclass__`.
   - `AuditEventFactory` keyed by the subclass-declaration kwarg: `class X(AuditEvent, action=AuditLogAction.ban)` ([events.py](../../../wd-core/src/wd_core/events.py)).
   - `BaseModel.__init_subclass__` auto-collects every model ([wd-db/src/wd_db/extension/model.py](../../../wd-db/src/wd_db/extension/model.py)).
   Registration happens at import time — a package `__init__` must import the modules containing the subclasses (see the note in `wd-errors/__init__.py`).

3. **Service locator (module singletons)** — reserved for process-wide resources: `engine`/`session` in [wd-db/src/wd_db/constants.py](../../../wd-db/src/wd_db/constants.py) (exposed via `SessionMixin`), and the static config classes (`Settings`, `DbUrl`). Don't create new module-level singletons for anything a constructor parameter can carry; the locator is the fallback, injection is the interface.

Decorator injection for config values: `@Config.with_kwarg("Tokens", "discord_token")` (see the config-and-constants skill).

## Avoiding repetition — the reuse toolbox, in order

1. **Import it.** Most duplication here started as a copy of an enum or helper (in-tree anti-examples: `Region`/`Platform` duplicated between `riot_clash_api.py` and `league_of_legends.py`; `steam_url.py` existing in both `wd-bot` and `wd-cogs`; `Cassiopeia*` protocols copied between two cogs). If two packages need it, move it down a layer (usually wd-types/wd-core), don't copy.
2. **Mixins** for orthogonal capabilities: `LoggerMixin` (herogold) gives `self.logger` everywhere; `SessionMixin` shares the DB session.
3. **Base classes with behavior**: `BaseModel` is a repository (`add/update/get/get_all/delete/fetch`); `Cog`/`GroupCog` hierarchy configures per-subclass `CogFlags` through `__init_subclass__`.
4. **Decorators** for cross-cutting policy: `returns_known_exception`, `with_known_exception`, `@loop`, `@Config.with_kwarg`.
5. **Descriptors/Protocols** for reusable field behavior and structural contracts — see the advanced-patterns skill.
