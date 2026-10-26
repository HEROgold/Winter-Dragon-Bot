# wd-discord

The in-house Discord API v10 client: REST transport, gateway, validated response models and client-bound entities. It replaces discord.py and is written from the Discord docs (<https://docs.discord.com/developers>).

- **Depends on:** `wd-config` and `wd-errors` (plus herogold, httpxyz, pydantic, websockets, sentry-sdk). Never imports wd-core/wd-db/wd-bot (enforced by `tests/test_layering.py`). Gateway `Intents` live in `intents.py`; outbound request bodies and `RequestKwargs` in `payloads.py`.
- **Start here:** `Client` (transport) → its stores `client.users`, `client.channels`, `client.guilds`, `client.application.commands` → entities in `entities/`. Data models in `resources/`, gateway in `gateway/`, `bind()` turns a dispatch into an entity.
- **Rules:** responses are `DiscordModel`s; every operation returns `T | NetworkError` instead of raising. See the `discord-api-models` skill.
- **Generated:** `src/wd_discord/gateway/dispatch.pyi` — regenerate with `uv run wd-discord/scripts/generate_dispatch_overloads.py`.
- **Entity coverage:** [entity-coverage.md](entity-coverage.md) tracks which Discord objects have entities and which still need a model.
- **Tests:** `wd-discord/tests/`, offline via `wd_discord.testing.RecordingClient`. Build Discord JSON with the `wd_discord.testing` builders (`user_json()`, `member_json()`, `guild_create_json()`, ...) instead of writing the dicts out. For property tests, `wd_discord.testing.strategies` draws the same objects with Hypothesis, within the limits the Discord docs give.
- **API reference:** [wd_discord](../docs/reference/wd-discord.md) · [entities](../docs/reference/wd-discord.entities.md) · [resources](../docs/reference/wd-discord.resources.md) · [gateway](../docs/reference/wd-discord.gateway.md) · [testing](../docs/reference/wd-discord.testing.md)
