"""Unit tests: automatic voice channels made by joining the hub, deleted once empty, and their commands (no network)."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, select
from wd_bot.registry import CommandRegistry
from wd_discord import Guild, Permissions, VoiceState, bind
from wd_discord.gateway import EventName, parse_dispatch
from wd_discord.gateway.events import InteractionDataOption, ResolvedData
from wd_discord.resources.channel import Channel as ChannelModel
from wd_discord.testing import GUILD_JSON, RecordingClient

from winter_dragon.cogs.autochannel import (
    OWNER_PERMISSIONS,
    AutoChannel,
    AutoChannelHub,
    AutoChannels,
    AutoChannelSettings,
)


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine


GUILD_ID = 1
HUB_ID = 50
CATEGORY_ID = 49
MEMBER_ID = 3
NEW_CHANNEL = {"id": "60", "type": 2, "guild_id": "1", "name": "asker's channel", "parent_id": str(CATEGORY_ID)}
MESSAGE_JSON = {
    "id": "5",
    "channel_id": "7",
    "author": {"id": "2", "username": "bot", "discriminator": "0"},
    "content": "",
    "timestamp": "2026-10-08T12:00:00+00:00",
    "tts": False,
    "mention_everyone": False,
}
MEMBER_JSON = {
    "user": {"id": str(MEMBER_ID), "username": "asker", "discriminator": "0"},
    "nick": None,
    "roles": [],
    "joined_at": None,
    "deaf": False,
    "mute": False,
}


def _state(client: RecordingClient, channel_id: int | None, user_id: int = MEMBER_ID) -> VoiceState:
    data = {
        "guild_id": str(GUILD_ID),
        "channel_id": None if channel_id is None else str(channel_id),
        "user_id": str(user_id),
        "member": {**MEMBER_JSON, "user": {"id": str(user_id), "username": "asker", "discriminator": "0"}},
        "session_id": "s",
        "deaf": False,
        "mute": False,
        "self_deaf": False,
        "self_mute": False,
        "self_video": False,
        "suppress": False,
        "request_to_speak_timestamp": None,
    }
    state = bind(client, parse_dispatch(EventName.VOICE_STATE_UPDATE, data))
    assert isinstance(state, VoiceState)
    return state


def _cog(engine: Engine, client: RecordingClient) -> AutoChannels:
    cog = AutoChannels.__new__(AutoChannels)
    cog.bot = SimpleNamespace(client=client, registry=CommandRegistry())  # pyright: ignore[reportAttributeAccessIssue]
    cog.session = Session(engine)
    cog.voice = defaultdict(dict)
    cog._lock = asyncio.Lock()  # noqa: SLF001 - what __init__ sets up
    return cog


def _seed(engine: Engine, *rows: object) -> None:
    with Session(engine) as session:
        session.add_all(rows)  # pyright: ignore[reportArgumentType]
        session.commit()


def _channels(engine: Engine) -> list[AutoChannel]:
    with Session(engine) as session:
        return list(session.exec(select(AutoChannel)))


@pytest.fixture
def client() -> RecordingClient:
    client = RecordingClient()
    client.reply("GET", f"/channels/{HUB_ID}", {"id": str(HUB_ID), "type": 2, "guild_id": "1", "parent_id": str(CATEGORY_ID)})
    client.reply("POST", f"/guilds/{GUILD_ID}/channels", NEW_CHANNEL)
    client.reply("PATCH", f"/guilds/{GUILD_ID}/members/{MEMBER_ID}", MEMBER_JSON)
    client.reply("DELETE", "/channels/60", NEW_CHANNEL)
    return client


async def test_joining_the_hub_creates_a_channel_and_moves_the_member_in(engine: Engine, client: RecordingClient) -> None:
    _seed(engine, AutoChannelHub(guild_id=GUILD_ID, channel_id=HUB_ID), AutoChannelSettings(user_id=MEMBER_ID, user_limit=4))

    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    (create,) = client.requests_to("POST", f"/guilds/{GUILD_ID}/channels")
    assert create.json == {
        "name": "asker's channel",
        "type": 2,
        "parent_id": str(CATEGORY_ID),
        "user_limit": 4,
        "permission_overwrites": [{"id": "3", "type": 1, "allow": str(int(OWNER_PERMISSIONS)), "deny": "0"}],
    }
    (move,) = client.requests_to("PATCH", f"/guilds/{GUILD_ID}/members/{MEMBER_ID}")
    assert move.json == {"channel_id": "60"}
    assert [(channel.owner_id, channel.channel_id) for channel in _channels(engine)] == [(MEMBER_ID, 60)]


async def test_an_owner_rejoining_the_hub_is_moved_to_their_channel(engine: Engine, client: RecordingClient) -> None:
    _seed(
        engine,
        AutoChannelHub(guild_id=GUILD_ID, channel_id=HUB_ID),
        AutoChannel(guild_id=GUILD_ID, owner_id=MEMBER_ID, channel_id=60),
    )

    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    assert client.requests_to("POST", f"/guilds/{GUILD_ID}/channels") == []
    assert client.requests_to("PATCH", f"/guilds/{GUILD_ID}/members/{MEMBER_ID}")[0].json == {"channel_id": "60"}


async def test_the_guild_limit_stops_new_channels(engine: Engine, client: RecordingClient) -> None:
    _seed(
        engine,
        AutoChannelHub(guild_id=GUILD_ID, channel_id=HUB_ID, max_channels=1),
        AutoChannel(guild_id=GUILD_ID, owner_id=99, channel_id=61),
    )
    client.reply("POST", "/users/@me/channels", {"id": "7", "type": 1})
    client.reply("POST", "/channels/7/messages", MESSAGE_JSON)

    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    assert client.requests_to("POST", f"/guilds/{GUILD_ID}/channels") == []
    assert "as many automatic channels as it allows" in client.requests_to("POST", "/channels/7/messages")[0].json["content"]


async def test_leaving_an_empty_channel_deletes_it(engine: Engine, client: RecordingClient) -> None:
    _seed(engine, AutoChannel(guild_id=GUILD_ID, owner_id=MEMBER_ID, channel_id=60))
    cog = _cog(engine, client)
    cog.voice[GUILD_ID] = {MEMBER_ID: 60, 4: 60}

    await cog.on_voice_state_update(_state(client, None))
    assert client.requests_to("DELETE", "/channels/60") == []  # someone is still in it

    await cog.on_voice_state_update(_state(client, None, user_id=4))
    assert len(client.requests_to("DELETE", "/channels/60")) == 1
    assert _channels(engine) == []


async def test_guild_create_cleans_up_channels_emptied_while_offline(engine: Engine, client: RecordingClient) -> None:
    _seed(
        engine,
        AutoChannel(guild_id=GUILD_ID, owner_id=MEMBER_ID, channel_id=60),
        AutoChannel(guild_id=GUILD_ID, owner_id=4, channel_id=61),
    )
    voice_state = {
        key: value for key, value in _state(client, 61, user_id=4).model.model_dump(mode="json").items() if key != "member"
    }
    guild = bind(client, parse_dispatch(EventName.GUILD_CREATE, {**GUILD_JSON, "voice_states": [voice_state]}))
    assert isinstance(guild, Guild)

    cog = _cog(engine, client)
    await cog.on_guild_create(guild)

    assert cog.voice[GUILD_ID] == {4: 61}
    assert [sent.path for sent in client.sent if sent.method == "DELETE"] == ["/channels/60"]
    assert [channel.channel_id for channel in _channels(engine)] == [61]


async def test_limit_is_saved_and_applied_to_the_owned_channel(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    _seed(engine, AutoChannel(guild_id=GUILD_ID, owner_id=MEMBER_ID, channel_id=60))
    discord_client.reply("PATCH", "/channels/60", NEW_CHANNEL)
    interaction = make_interaction(
        "autochannel", options=[InteractionDataOption(name="limit", type=4, value=5)], guild_id=GUILD_ID
    )

    await AutoChannels.set_limit.invoke(_cog(engine, discord_client), interaction, interaction.options)

    assert discord_client.requests_to("PATCH", "/channels/60")[0].json == {"user_limit": 5}
    with Session(engine) as session:
        assert session.exec(select(AutoChannelSettings)).one().user_limit == 5


async def test_limit_out_of_range_is_refused(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    interaction = make_interaction(
        "autochannel", options=[InteractionDataOption(name="limit", type=4, value=100)], guild_id=GUILD_ID
    )

    await AutoChannels.set_limit.invoke(_cog(engine, discord_client), interaction, interaction.options)

    assert discord_client.interaction_responses()[0]["data"]["content"] == "Give me 0 for no limit, or up to 99."


async def test_mark_needs_manage_server(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    hub = ChannelModel.model_validate({"id": str(HUB_ID), "type": 2, "name": "Join me"})
    interaction = make_interaction(
        "autochannel",
        options=[InteractionDataOption(name="channel", type=7, value=str(HUB_ID))],
        resolved=ResolvedData(channels={str(HUB_ID): hub}),
        guild_id=GUILD_ID,
        permissions=Permissions.MANAGE_CHANNELS,
    )

    await AutoChannels.mark.invoke(_cog(engine, discord_client), interaction, interaction.options)

    assert discord_client.interaction_responses()[0]["data"]["content"] == "You need the Manage Server permission for that."
