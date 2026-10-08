# wd-bot

The bot framework built on wd-discord: `Bot` (lifecycle, gateway, dispatch), `Cog`/`GroupCog`, slash commands, component handlers, autocomplete, help and application-command sync.

- **Depends on:** wd-config, wd-core, wd-discord, wd-errors, wd-types (and imports `wd_db` without declaring it — known debt).
- **Start here:** `wd_bot.bot.Bot(extensions_package=...)` → `start()`. Cogs subclass `wd_bot.cogs.Cog`/`GroupCog`; commands come from `@Cog.command`, buttons from `@Cog.component`, events from `@Cog.listener`.
- **Not features:** feature cogs live in `src/winter_dragon/cogs/`, not here.
- **Generated:** `src/wd_bot/listener.pyi` — regenerate with `uv run wd-bot/scripts/generate_listener_overloads.py`.
- **Tests:** `wd-bot/tests/` (also covers the `winter_dragon` cogs).
- **API reference:** [wd_bot](../docs/reference/wd-bot.md)
