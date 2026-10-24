<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord.testing` (wd-discord)
Test helpers for code built on wd-discord: a client that records its requests, and Discord JSON payloads.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord.testing` — `wd-discord/src/wd_discord/testing/__init__.py`

- exports: GUILD_JSON, TEST_APPLICATION_ID, TEST_TOKEN, RecordingClient, SentRequest, bot_user_json, channel_json,
  guild_create_json, member_json, message_json, role_json, thread_json, user_json, voice_state_json

## `wd_discord.testing.client` — `wd-discord/src/wd_discord/testing/client.py`
Test doubles for code built on wd-discord.

- module names: TEST_TOKEN, TEST_APPLICATION_ID

### `@dataclass class SentRequest`
One request a :class:`RecordingClient` received.

- fields: method: str, path: str, json: Any, data: Any, files: Any, headers: Any, params: Any

### `class RecordingClient(Client)`
A client that records requests instead of sending them, and answers with canned replies.

- `reply(method: str, path: str, body: Mapping[str, object] | list[Any] | None=None, *, status: int=200) -> None` — Answer every ``method`` request to ``path`` with ``body`` as JSON (no body when ``None``).
- `reply_each(method: str, path: str, *bodies: Mapping[str, object]) -> None` — Answer the next ``method`` requests to ``path`` with ``bodies`` in turn, then fall back to :meth:`reply`'s.
- `fail(method: str, path: str, error: ApiResponseError) -> None` — Answer every ``method`` request to ``path`` with ``error``.
- `requests_to(method: str, path: str) -> list[SentRequest]` — Return the recorded ``method`` requests to ``path``, oldest first.
- `interaction_responses() -> list[Any]` — Return the bodies of every initial interaction response sent, oldest first.

## `wd_discord.testing.payloads` — `wd-discord/src/wd_discord/testing/payloads.py`
Discord JSON payloads for tests, shaped as the Discord docs describe each object.

- module names: GUILD_JSON: Mapping[str, object]
- `user_json(**fields: Any) -> dict[str, Any]` — Return user 3, ``someone``, with ``fields`` changed.
- `bot_user_json(**fields: Any) -> dict[str, Any]` — Return the bot's own user, 2 (``RecordingClient``'s application ID), with ``fields`` changed.
- `member_json(**fields: Any) -> dict[str, Any]` — Return user 3 as a guild member without roles, with ``fields`` changed.
- `role_json(**fields: Any) -> dict[str, Any]` — Return role 8, ``mods``, without permissions, with ``fields`` changed.
- `channel_json(**fields: Any) -> dict[str, Any]` — Return text channel 5, ``general``, in guild 7, with ``fields`` changed.
- `thread_json(**fields: Any) -> dict[str, Any]` — Return public thread 6 in channel 5, open, with ``fields`` changed.
- `voice_state_json(**fields: Any) -> dict[str, Any]` — Return user 3 connected to channel 5, nothing muted, with ``fields`` changed.
- `message_json(**fields: Any) -> dict[str, Any]` — Return message 5 the bot sent in channel 6, without content, with ``fields`` changed.
- `guild_create_json(**fields: Any) -> dict[str, Any]` — Return guild 7 as GUILD_CREATE sends it, with ``fields`` changed.
