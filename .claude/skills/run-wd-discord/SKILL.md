---
name: run-wd-discord
description: Run and drive the Winter Dragon Discord bot / wd-discord client live against Discord — the real bot entry point, a time-boxed sqlite test bot, the REST/gateway smoke driver and the verify_* drivers. Use when asked to run the bot, start the Discord client, verify a wd-discord change against the live API, or smoke-test gateway/REST behavior.
---

# Run: the Discord bot and client (live)

All paths relative to the repo root. Everything here needs a real bot token in `config.ini` under `[Tokens] discord_token`; `!!` is the "unset" sentinel. Never print `config.ini`.

## Which one to run

| Goal | Command |
|---|---|
| Whole bot, time-boxed, no Postgres | `uv run python -m winter_dragon.run_test_bot` — real `wd_bot.Bot` with `winter_dragon.cogs`, local sqlite engine, stops after 10 minutes |
| Whole bot, production shape | `uv run python -m winter_dragon` — `Bot(extensions_package=cogs).start()`; needs Postgres (`DbUrl` config + psycopg2) |
| REST auth + gateway handshake only | `uv run python .claude/skills/run-wd-discord/driver.py` |
| Live checks of one area | `uv run python .claude/skills/run-wd-discord/verify_{rest,gateway,models,emoji,sentry}.py`, or `verify_all.py` for all |
| Gateway dispatch → `parse_dispatch` | `uv run python tests/verify_bot_events.py [seconds]` |

## Smoke driver output (verified 2026-07-07)

```text
REST OK: authenticated as TBot (id 12268...)
REST OK: gateway url wss://gateway.discord.gg, recommended shards 1
GATEWAY OK: READY session 3bb18e2b..., user TBot
GATEWAY OK: closed cleanly
```

The driver calls `client.users.me()` and `client.get_gateway_bot()` (errors-as-values — a failure is a `NetworkError`, checked with `is_network_error`), then `Gateway.connect()` through HELLO → IDENTIFY → READY and `Gateway.close()`. Extend a driver rather than writing throwaway scripts.

## Direct invocation

Most wd-discord changes touch one function. The outbound builders in `wd_discord/gateway/connection.py` (`build_presence`, `build_identify`, `parse_ready`) are pure — call them directly:

```powershell
uv run python -c "from wd_discord.gateway.connection import build_presence; print(build_presence())"
```

Check a signature in [docs/reference/wd-discord.gateway.md](../../../docs/reference/wd-discord.gateway.md) first.

## Gotchas

- `Gateway.connect()` blocks until READY; wrap it in `asyncio.wait_for(..., timeout=30)` like the driver does, or a bad token hangs the run.
- `wd_db.constants` creates a Postgres engine at import time; on a host without psycopg2 use `run_test_bot` (it stubs a sqlite engine), not `python -m winter_dragon`.
- `Bot.start()`'s `token` is injected by `@Config.with_kwarg`, so type checkers report it missing — the call site carries a coded `# ty: ignore`.
