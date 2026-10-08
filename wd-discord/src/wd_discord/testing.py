"""Test doubles for code built on wd-discord.

:class:`RecordingClient` is a real :class:`~wd_discord.client.Client` whose transport never touches the
network: it records every request and answers from canned replies. Stores and entities run unchanged on
top of it, so a test asserts on the HTTP calls an action made::

    client = RecordingClient()
    client.reply("POST", "/channels/6/messages", {...message json...})
    await client.channels.partial(6).send("hi")
    assert client.sent[-1].json == {"content": "hi"}
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Any, override

lazy from httpxyz import Request, Response

lazy from wd_discord.client import Client


if TYPE_CHECKING:
    from collections.abc import Mapping

    from wd_discord.errors.api import ApiResponseError
    from wd_discord.snowflake import SnowflakeLike


TEST_TOKEN = "token"  # noqa: S105 - a placeholder; RecordingClient never sends it anywhere
TEST_APPLICATION_ID = 2

GUILD_JSON: Mapping[str, object] = {
    "id": "1",
    "name": "My Guild",
    "icon": None,
    "splash": None,
    "discovery_splash": None,
    "owner_id": "9",
    "afk_channel_id": None,
    "afk_timeout": 300,
    "verification_level": 0,
    "default_message_notifications": 0,
    "explicit_content_filter": 0,
    "roles": [],
    "emojis": [],
    "features": [],
    "mfa_level": 0,
    "application_id": None,
    "system_channel_id": None,
    "system_channel_flags": 0,
    "rules_channel_id": None,
    "vanity_url_code": None,
    "description": None,
    "banner": None,
    "premium_tier": 0,
    "preferred_locale": "en-US",
    "public_updates_channel_id": None,
    "nsfw_level": 0,
    "premium_progress_bar_enabled": False,
    "safety_alerts_channel_id": None,
    "incidents_data": None,
}
"""The smallest guild object Discord could send: every required field, nothing optional."""


@dataclass(frozen=True)
class SentRequest:
    """One request a :class:`RecordingClient` received."""

    method: str
    path: str
    json: Any = None
    data: Any = None
    """The form fields of a ``multipart/form-data`` request, e.g. a message with files."""
    files: Any = None


class RecordingClient(Client):
    """A client that records requests instead of sending them, and answers with canned replies.

    A request without a reply gets an empty ``204 No Content``, which is what Discord answers to interaction
    callbacks and deletes.
    """

    def __init__(self, *, application_id: SnowflakeLike | None = TEST_APPLICATION_ID) -> None:
        """Build a client whose application ID is ``application_id`` (``None`` makes it look the ID up)."""
        super().__init__(TEST_TOKEN, application_id=application_id)
        self.sent: list[SentRequest] = []
        self._replies: dict[tuple[str, str], Response | ApiResponseError] = {}

    def reply(self, method: str, path: str, body: Mapping[str, object] | list[Any] | None = None, *, status: int = 200) -> None:
        """Answer every ``method`` request to ``path`` with ``body`` as JSON (no body when ``None``)."""
        request = Request(method, f"{self.base_url}{path}")
        response = Response(status, request=request) if body is None else Response(status, json=body, request=request)
        self._replies[method, path] = response

    def fail(self, method: str, path: str, error: ApiResponseError) -> None:
        """Answer every ``method`` request to ``path`` with ``error``."""
        self._replies[method, path] = error

    def requests_to(self, method: str, path: str) -> list[SentRequest]:
        """Return the recorded ``method`` requests to ``path``, oldest first."""
        return [sent for sent in self.sent if sent.method == method and sent.path == path]

    def interaction_responses(self) -> list[Any]:
        """Return the bodies of every initial interaction response sent, oldest first."""
        return [
            sent.json
            for sent in self.sent
            if sent.method == "POST" and sent.path.startswith("/interactions/") and sent.path.endswith("/callback")
        ]

    @override
    async def request(self, method: str, path: str, **kwargs: Any) -> Response | ApiResponseError:  # pyright: ignore[reportIncompatibleMethodOverride] - the parent's decorator widens its declared return
        """Record the request and return its canned reply."""
        self.sent.append(SentRequest(method, path, kwargs.get("json"), kwargs.get("data"), kwargs.get("files")))
        reply = self._replies.get((method, path))
        if reply is None:
            return Response(204, request=Request(method, f"{self.base_url}{path}"))
        return reply
