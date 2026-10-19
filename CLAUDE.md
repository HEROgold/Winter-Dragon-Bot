# CLAUDE.md

## Finding code

- **API lookups start in [docs/reference/](docs/reference/index.md)**: one generated page per package or first-level subpackage (`wd-discord.entities.md`, `winter-dragon.cogs.md`, ...), listing each public class, field, signature and docstring line with its source file. `Grep` for the symbol in `docs/reference/` to get its signature and file in one call, then open the source at that symbol only when you need a body.
- **Package purpose and boundaries:** each `wd-*/README.md` (what it owns, what it may depend on, where to start).
- **Live feature code is `src/winter_dragon/cogs/`**, built on `wd_bot` (`Cog`, `@Cog.command`, `@Cog.component`, `@Cog.listener`); its tests are in `wd-bot/tests/`. `wd-cogs` is the legacy discord.py catalog — port from it, build in `winter_dragon/cogs/`.

## Database changes

A model change (a `table=True` class: new table, column, type, index) needs an Alembic revision before its PR can merge. Don't write it with the model change: the **Auto-migrate** workflow generates it into a migration PR stacked on yours (`migration/<branch>`); read and fix the generated file there, then merge it into your branch. To generate one locally instead: `uv run python -m winter_dragon.migrations --url <scratch postgres> revision -m "..."`. Never point `--url` at the live database. See [docs/dev/database.md](docs/dev/database.md#migrations).

## Generated files

Regenerate these with their script after changing what they describe; pre-commit checks them:

- `docs/reference/` — `uv run python scripts/generate_api_reference.py` after any public API change.
- `wd-discord/src/wd_discord/gateway/dispatch.pyi` — `uv run wd-discord/scripts/generate_dispatch_overloads.py`.
- `wd-bot/src/wd_bot/listener.pyi` — `uv run wd-bot/scripts/generate_listener_overloads.py`.

Docs and skills link to files and name symbols (``client.py `returns_known_exception` ``); `scripts/check_doc_links.py` rejects broken links and `#L` line anchors.

## Import style

Prefer lazy imports (import inside the function/method that uses the name) over module-level imports. Module-level imports are only used when required by the tooling/library itself (e.g. pydantic needs types resolvable at class-definition time).

## Agent skills

### Issue tracker

GitHub Issues on HEROgold/Winter-Dragon-Bot via `gh`; new issues auto-sync to Linear. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
