"""Unit tests: Client.create_interaction_response's callback payload (no network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from wd_discord import Client


if TYPE_CHECKING:
    import pytest


async def _captured_payload(monkeypatch: pytest.MonkeyPatch, **kwargs: object) -> dict[str, object]:
    """Call create_interaction_response with ``kwargs`` and return the JSON body it POSTed."""
    client = Client("token")
    sent: dict[str, object] = {}

    async def fake_post(path: str, **post_kwargs: object) -> None:
        sent["path"] = path
        sent["json"] = post_kwargs["json"]

    monkeypatch.setattr(client, "post", fake_post)
    interaction = SimpleNamespace(id="1", token="tok")  # noqa: S106
    await client.create_interaction_response(interaction, **kwargs)  # type: ignore[arg-type]
    assert sent["path"] == "/interactions/1/tok/callback"
    payload = sent["json"]
    assert isinstance(payload, dict)
    return payload


async def test_ephemeral_sets_flag_64(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = await _captured_payload(monkeypatch, content="hi", ephemeral=True)
    assert payload == {"type": 4, "data": {"content": "hi", "flags": 64}}


async def test_not_ephemeral_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = await _captured_payload(monkeypatch, content="hi")
    assert payload == {"type": 4, "data": {"content": "hi"}}
