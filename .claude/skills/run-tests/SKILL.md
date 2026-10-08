---
name: run-tests
description: Run the WinterDragonV2 test suite with uv/pytest, including where each package's tests live and how live/integration tests are gated. Use when asked to run tests, verify a change with pytest, or check whether the suite is green.
---

# Run: tests

All paths relative to the repo root. Test config lives in the root `pyproject.toml` (`asyncio_mode = "auto"`, `--import-mode=importlib`). `testpaths` covers `wd-discord/tests` and `wd-bot/tests`; other packages have no tests yet. Add a package's `tests/` dir to `testpaths` when it gets some.

## The command (verified 2026-10-09)

```powershell
uv run pytest -q
```

Result: `415 passed, 10 skipped, 2 xfailed` in ~8s. The skips are live-API tests that auto-skip without a real token.

Scope it while iterating:

```powershell
uv run pytest wd-discord/tests/test_snowflake.py -q
uv run pytest wd-bot/tests -k steam -q
```

## Where tests live

- `wd-discord/tests/` — client, models, entities, gateway. Offline tests use `wd_discord.testing.RecordingClient` (canned `reply(...)`/`fail(...)`), not mocks.
- `wd-bot/tests/` — the bot framework **and** the app cogs in `src/winter_dragon/cogs/` (`test_steam_*`, `test_fuel_cog`, `test_reminder_cog`, ...). Shared sqlite engine and interaction builder are in `wd-bot/tests/conftest.py`.
- Root `tests/` holds live verification drivers (`verify_*.py`), not pytest tests — see run-wd-discord.

## Live/integration tests

`wd-discord/tests/conftest.py` builds a real `Client` from `config.ini`'s `[Tokens] discord_token` and skips when the token is the `!!` placeholder. Integration-marked tests hit the real Discord API — run them deliberately: `uv run pytest -m integration`.

## Gotchas

- A collection error stops the whole run (`Interrupted: N errors during collection`) before any test executes — a red run doesn't mean the other tests regressed. Fix the import, or scope with `--ignore` to see the rest.
- Generated stubs are checked on pre-push, not by pytest: `wd-discord/scripts/generate_dispatch_overloads.py --check`, `wd-bot/scripts/generate_listener_overloads.py --check`. Regenerate them after changing `EventName` or event entities.
