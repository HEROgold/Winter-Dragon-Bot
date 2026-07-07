---
name: run-tests
description: Run the WinterDragonV2 test suite with uv/pytest, including which tests are currently broken and how to run the passing subset. Use when asked to run tests, verify a change with pytest, or check whether the suite is green.
---

# Run: tests

All paths relative to the repo root. Test config lives in the root `pyproject.toml` (`asyncio_mode = "auto"`, `--import-mode=importlib`); only `wd-discord/tests` is wired into `testpaths` — other packages have no tests yet.

## The command that works (verified 2026-07-07)

A bare `uv run pytest` currently **fails at collection** (see Gotchas). Run the passing subset:

```powershell
uv run pytest -q --ignore=wd-discord/tests/test_rate_limit.py --ignore=wd-discord/tests/test_errors.py --ignore=wd-discord/tests/test_gateway.py
```

Verified result: `46 passed, 2 skipped in 2.05s`. The skips are live-API tests that auto-skip when not opted in.

Single file / single test:

```powershell
uv run pytest wd-discord/tests/test_snowflake.py -q
uv run pytest wd-discord/tests/test_gateway_payload.py -k ready -q
```

## Live/integration tests

`conftest.py` builds a real `Client` from `config.ini`'s `[Tokens] discord_token` and skips when the token is the `!!` placeholder. Integration-marked tests hit the real Discord API — only run them deliberately: `uv run pytest -m integration`.

## Gotchas (why the full suite is red)

- `test_rate_limit.py` — collection error: `TypeError: <class 'herogold.supports.SupportsDelete'> is not a generic class`. Upstream bug: herogold 3.6.0's `protocols` module doesn't import on Python 3.15; anything importing `wd_discord.utils` or `wd_discord.rate_limit` hits it. Not fixable in this repo; re-check after a herogold upgrade.
- `test_errors.py` and `test_gateway.py` — collection errors from the in-progress wd-discord restructure: they import names (`Activity`, `Gateway`, `GatewayActivity`, `Status`) from `wd_discord`'s top level that moved into `wd_errors.base` / `wd_discord.gateway.connection` and are not re-exported yet. These are real breakage in the working tree, not environment issues — fix the imports or the `__init__` re-exports, don't just ignore the files forever.
- pytest collection failure exits before running anything (`Interrupted: N errors during collection`) — a red full run does NOT mean the passing tests regressed; scope with `--ignore` to see the true state.
