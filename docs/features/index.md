# Feature Inventory (`main` branch)

This section is an **abstract inventory of everything the Winter Dragon bot does on the `main` branch** — the feature-complete implementation that predates the `v2` workspace rewrite.

It exists because `v2` splits the bot into `wd-*` packages and, in the process, lost the single place where "what the bot actually offers" was visible. These pages describe capabilities, not commands: what each feature is for and who uses it, with just enough surface detail (the command group, the trigger) to find it. For argument-level detail, read the source on `main`.

Every feature carries a **v2 parity status** so this doubles as the porting checklist for the rewrite.

## Status legend

| Status | Meaning |
|---|---|
| ✅ **Ported** | A counterpart exists in a `wd-*` package and its imports resolve inside the `v2` workspace. |
| 🟡 **Copied, unwired** | The file was lifted into `wd-cogs`/`wd-bot` but still imports `winter_dragon.*` modules that do not exist on `v2`. The code is there; it cannot import. |
| ❌ **Missing** | No counterpart on `v2` at all. |

!!! warning "`v2` does not run yet"
    A 🟡 or ✅ marker describes *code presence and import resolution only*. `v2` currently has no bot entrypoint, no database table models, and no API or worker services — see [TODO.md](https://github.com/HEROgold/Winter-Dragon-Bot/blob/v2/TODO.md). Nothing in this inventory has been verified end-to-end on `v2`.

## Areas

| Area | What it covers | Overall parity |
|---|---|---|
| [Bot Core](bot-core.md) | Extension loading, hot reload, command sync, config, errors, telemetry | ✅ mostly ported (runtime), 🟡 for the operator cogs |
| [Moderation & Logging](moderation.md) | Audit-log pipeline, log channels, gatekeeper, infractions, synced bans, purge | 🟡 event pipeline ported, cogs unwired |
| [Server Management](server-management.md) | Auto-assign, autochannel, welcome, stats, announcements, guild scaffolding | 🟡 across the board |
| [Games](games.md) | Hangman, incremental, LFG, question games, League of Legends, Clash | 🟡 except the Riot API client |
| [User Tools](user-tools.md) | Steam sales, reminders, fuel tracking, Urban Dictionary, invites, team splitting | 🟡 except the stateless Steam helpers |
| [Platform & Services](platform.md) | REST API, frontend, task queue, workers, metrics, data layer, Docker stack | ❌ largely missing |

## The shape of the gap

Two structural gaps explain almost every 🟡 in this inventory:

- **Database models.** `main` ships ~60 SQLModel tables under `src/winter_dragon/database/tables/`. On `v2`, `wd-db` has the extension/model machinery but **no `tables/` package at all**. Nearly every stateful cog imports from it.
- **The UI toolkit.** `main` ships a shared `src/winter_dragon/bot/ui/` package (buttons, menus, modals, selects, views, and a paginator). It has **no `wd-*` home on `v2`**, yet the log aggregator, hangman, command manager, sync, welcome, and the Steam sales menu all import it.

Closing those two unblocks the bulk of the cogs, which are otherwise verbatim copies.

Alongside them: the FastAPI service, the React frontend, and the Redis/RQ queue plus worker runner and autoscaler have no `v2` counterpart yet.

## Reading these pages

- **Source on `main`** lines give the path to read for detail — resolve them with `git show main:<path>`.
- Features that were **already incomplete on `main`** are flagged as such. They are not porting gaps; they were never finished.
