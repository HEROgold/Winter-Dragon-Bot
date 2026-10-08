"""Unit tests: the /uptime and /invite commands (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from wd_config.bot import Settings
from wd_discord.permissions import ChannelType
from wd_discord.testing import GUILD_JSON, RecordingClient

from winter_dragon.cogs.invite import Invite
from winter_dragon.cogs.uptime import Uptime, uptime_message


if TYPE_CHECKING:
    from collections.abc import Mapping

    from conftest import InteractionFactory


SUPPORT_GUILD_ID = 77


def _content(discord_client: RecordingClient) -> str:
    return discord_client.interaction_responses()[0]["data"]["content"]


def test_uptime_message_shows_absolute_and_relative_time() -> None:
    launch = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
    epoch = int(launch.timestamp())
    assert uptime_message(launch) == f"Online since <t:{epoch}:F> (<t:{epoch}:R>)"


async def test_uptime_replies_with_the_launch_time(
    make_interaction: InteractionFactory, discord_client: RecordingClient
) -> None:
    launch = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
    cog = Uptime.__new__(Uptime)
    cog.bot = SimpleNamespace(launch_time=launch)  # pyright: ignore[reportAttributeAccessIssue]

    await Uptime.bot_uptime.invoke(cog, make_interaction("uptime"), [])

    assert _content(discord_client) == uptime_message(launch)


@pytest.fixture
def support_guild(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Settings, "support_guild_id", SUPPORT_GUILD_ID)


def _invite_cog(
    guild: Mapping[str, object], channels: list[Mapping[str, object]] | None = None
) -> tuple[Invite, RecordingClient]:
    client = RecordingClient()
    client.reply("GET", f"/guilds/{SUPPORT_GUILD_ID}", guild)
    client.reply("GET", f"/guilds/{SUPPORT_GUILD_ID}/channels", channels or [])
    for channel_id in ("10", "11"):
        client.reply("POST", f"/channels/{channel_id}/invites", {"code": f"code{channel_id}"})
    cog = Invite.__new__(Invite)
    cog.bot = SimpleNamespace(client=client)  # pyright: ignore[reportAttributeAccessIssue]
    return cog, client


@pytest.mark.usefixtures("support_guild")
async def test_support_invite_uses_the_system_channel(
    make_interaction: InteractionFactory, discord_client: RecordingClient
) -> None:
    cog, client = _invite_cog({**GUILD_JSON, "id": str(SUPPORT_GUILD_ID), "system_channel_id": "10"})

    await Invite.support_invite.invoke(cog, make_interaction("invite"), [])

    (sent,) = client.requests_to("POST", "/channels/10/invites")
    assert (sent.json["max_age"], sent.json["max_uses"]) == (60, 1)
    assert _content(discord_client) == "https://discord.gg/code10"


@pytest.mark.usefixtures("support_guild")
async def test_support_invite_falls_back_to_the_first_text_channel(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    channels: list[Mapping[str, object]] = [
        {"id": "12", "type": ChannelType.GUILD_VOICE, "guild_id": str(SUPPORT_GUILD_ID)},
        {"id": "11", "type": ChannelType.GUILD_TEXT, "guild_id": str(SUPPORT_GUILD_ID)},
    ]
    cog, _ = _invite_cog({**GUILD_JSON, "id": str(SUPPORT_GUILD_ID), "system_channel_id": None}, channels)

    await Invite.support_invite.invoke(cog, make_interaction("invite"), [])

    assert _content(discord_client) == "https://discord.gg/code11"


@pytest.mark.usefixtures("support_guild")
async def test_support_invite_without_a_channel_says_so(
    make_interaction: InteractionFactory, discord_client: RecordingClient
) -> None:
    cog, _ = _invite_cog({**GUILD_JSON, "id": str(SUPPORT_GUILD_ID), "system_channel_id": None})

    await Invite.support_invite.invoke(cog, make_interaction("invite"), [])

    assert _content(discord_client) == "I couldn't create an invite to the support guild."


async def test_support_invite_without_a_support_guild(
    monkeypatch: pytest.MonkeyPatch,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    monkeypatch.setattr(Settings, "support_guild_id", 0)
    cog, client = _invite_cog(GUILD_JSON)

    await Invite.support_invite.invoke(cog, make_interaction("invite"), [])

    assert client.sent == []
    assert _content(discord_client) == "There is no support guild set up."
