"""Unit tests: the Client's interaction-response and message payloads (no network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from wd_discord import Client
from wd_discord.components import ActionRow, Button, ButtonStyle
from wd_discord.embed import Embed
from wd_discord.gateway.events import CommandInteraction, InteractionData, InteractionType


if TYPE_CHECKING:
    import pytest


INTERACTION = CommandInteraction(
    id="1",
    application_id="2",
    type=InteractionType.APPLICATION_COMMAND,
    token="tok",  # noqa: S106
    version=1,
    data=InteractionData(id="10", name="c", type=1),
)
ROW = ActionRow(components=[Button(style=ButtonStyle.SECONDARY, label="Next", custom_id="next")])
ROW_JSON = [{"type": 1, "components": [{"type": 2, "style": 2, "label": "Next", "custom_id": "next", "disabled": False}]}]
MESSAGE_JSON = {
    "id": "5",
    "channel_id": "6",
    "author": {"id": "2", "username": "bot", "discriminator": "0"},
    "content": "",
    "timestamp": "2026-10-08T00:00:00+00:00",
    "tts": False,
    "mention_everyone": False,
}


def _capture(monkeypatch: pytest.MonkeyPatch, client: Client, method: str) -> dict[str, object]:
    """Replace ``client.<method>`` with a recorder of the path and JSON body it's called with."""
    sent: dict[str, object] = {}

    async def fake(path: str, **kwargs: object) -> object:
        sent["path"] = path
        sent["json"] = kwargs["json"]
        return SimpleNamespace(json=lambda: MESSAGE_JSON)

    monkeypatch.setattr(client, method, fake)
    return sent


async def test_ephemeral_sets_flag_64(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "post")
    await client.create_interaction_response(INTERACTION, content="hi", ephemeral=True)
    assert sent == {"path": "/interactions/1/tok/callback", "json": {"type": 4, "data": {"content": "hi", "flags": 64}}}


async def test_not_ephemeral_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "post")
    await client.create_interaction_response(INTERACTION, content="hi")
    assert sent["json"] == {"type": 4, "data": {"content": "hi"}}


async def test_response_can_carry_components(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "post")
    await client.create_interaction_response(INTERACTION, content="hi", components=[ROW])
    assert sent["json"] == {"type": 4, "data": {"content": "hi", "components": ROW_JSON}}


async def test_defer_sends_type_5_without_data(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "post")
    await client.defer_interaction(INTERACTION)
    assert sent == {"path": "/interactions/1/tok/callback", "json": {"type": 5}}


async def test_ephemeral_defer_sets_flag_64(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "post")
    await client.defer_interaction(INTERACTION, ephemeral=True)
    assert sent["json"] == {"type": 5, "data": {"flags": 64}}


async def test_update_message_sends_type_7(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "post")
    await client.update_interaction_message(INTERACTION, embeds=[Embed(title="p2")], components=[ROW])
    assert sent["json"] == {"type": 7, "data": {"embeds": [{"title": "p2"}], "components": ROW_JSON}}


async def test_edit_original_patches_the_webhook_message(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "patch")
    message = await client.edit_original_interaction_response(INTERACTION, embeds=[Embed(title="p1")])
    assert sent == {"path": "/webhooks/2/tok/messages/@original", "json": {"embeds": [{"title": "p1"}]}}
    assert str(getattr(message, "id", "")) == "5"


async def test_edit_original_with_empty_components_clears_them(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "patch")
    await client.edit_original_interaction_response(INTERACTION, components=[])
    assert sent["json"] == {"components": []}


async def test_create_message_sends_embeds_and_components(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client("token")
    sent = _capture(monkeypatch, client, "post")
    await client.create_message("6", "hello", embeds=[Embed(title="sales")], components=[ROW])
    assert sent == {
        "path": "/channels/6/messages",
        "json": {"content": "hello", "embeds": [{"title": "sales"}], "components": ROW_JSON},
    }
