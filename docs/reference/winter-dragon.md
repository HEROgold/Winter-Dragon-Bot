<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon` (winter-dragon)

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.config` — `src/winter_dragon/config.py`
The app's own config scopes: cog settings in ``cogs.ini``.

- module names: COGS_CONFIG_FILE

### `class CogConfig[T](Config[T])`
Config descriptor scoped to the cog settings file; every cog shares it, one section per settings class.

## `winter_dragon.run_test_bot` — `src/winter_dragon/run_test_bot.py`
Run a real wd_bot.Bot for up to 10 minutes against the live Discord API.

- module names: RUN_DURATION_SECONDS
- `async main() -> int` — Run the bot for up to RUN_DURATION_SECONDS, then report the outcome.
