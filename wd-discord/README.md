# wd-discord

The in-house Discord API v10 client: REST transport, gateway, validated response models and client-bound entities. It replaces discord.py and is written from the Discord docs (<https://docs.discord.com/developers>).

- **Depends on:** `wd-config` only (plus herogold, httpxyz, pydantic, websockets, sentry-sdk). Never imports wd-core/wd-db/wd-bot.
- **Start here:** `Client` (transport) → its stores `client.users`, `client.channels`, `client.guilds`, `client.application.commands` → entities in `entities/`. Data models in `resources/`, gateway in `gateway/`, `bind()` turns a dispatch into an entity.
- **Rules:** responses are `DiscordModel`s; every operation returns `T | NetworkError` instead of raising. See the `discord-api-models` skill.
- **Generated:** `src/wd_discord/gateway/dispatch.pyi` — regenerate with `uv run wd-discord/scripts/generate_dispatch_overloads.py`.
- **Entity coverage:** [entity-coverage.md](entity-coverage.md) tracks which Discord objects have entities and which still need a model.
- **Tests:** `wd-discord/tests/`, offline via `wd_discord.testing.RecordingClient`.
- **API reference:** [wd_discord](../docs/reference/wd-discord.md) · [entities](../docs/reference/wd-discord.entities.md) · [resources](../docs/reference/wd-discord.resources.md) · [gateway](../docs/reference/wd-discord.gateway.md)
