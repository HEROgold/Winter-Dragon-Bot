"""Unit tests: automatic voice channels made by joining the hub, deleted once empty, and their commands (no network)."""

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive
from wd_db.testing import seed
from wd_discord import Guild, Permissions, VoiceState, bind
from wd_discord.gateway import EventName, parse_dispatch
from wd_discord.gateway.events import InteractionDataOption, ResolvedData
from wd_discord.resources.channel import Channel as ChannelModel
from wd_discord.snowflake import Snowflake
from wd_discord.testing import GUILD_JSON, RecordingClient, member_json, message_json, user_json, voice_state_json

from winter_dragon.cogs.autochannel import (
    OWNER_PERMISSIONS,
    AutoChannel,
    AutoChannelHub,
    AutoChannels,
    AutoChannelSettings,
    VoiceOccupancy,
)


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine


GUILD_ID = 1
HUB_ID = 50
CATEGORY_ID = 49
MEMBER_ID = 3
NEW_CHANNEL = {"id": "60", "type": 2, "guild_id": "1", "name": "asker's channel", "parent_id": str(CATEGORY_ID)}
MESSAGE_JSON = message_json(channel_id="7")
MEMBER_JSON = member_json(user=user_json(id=str(MEMBER_ID), username="asker"), nick=None)


def _state(client: RecordingClient, channel_id: int | None, user_id: int = MEMBER_ID) -> VoiceState:
    data = voice_state_json(
        guild_id=str(GUILD_ID),
        channel_id=None if channel_id is None else str(channel_id),
        user_id=str(user_id),
        member={**MEMBER_JSON, "user": user_json(id=str(user_id), username="asker")},
    )
    state = bind(client, parse_dispatch(EventName.VOICE_STATE_UPDATE, data))
    assert isinstance(state, VoiceState)
    return state


def _cog(engine: Engine, client: RecordingClient) -> AutoChannels:
    cog = detached_cog(AutoChannels, engine=engine, client=client)
    cog.voice = VoiceOccupancy()
    cog._lock = asyncio.Lock()  # noqa: SLF001 - what __init__ sets up
    return cog


def _channels(engine: Engine) -> list[AutoChannel]:
    with Session(engine) as session:
        return list(session.exec(alive(AutoChannel)))


@pytest.fixture
def client() -> RecordingClient:
    client = RecordingClient()
    client.reply("GET", f"/channels/{HUB_ID}", {"id": str(HUB_ID), "type": 2, "guild_id": "1", "parent_id": str(CATEGORY_ID)})
    client.reply("POST", f"/guilds/{GUILD_ID}/channels", NEW_CHANNEL)
    client.reply("PATCH", f"/guilds/{GUILD_ID}/members/{MEMBER_ID}", MEMBER_JSON)
    client.reply("DELETE", "/channels/60", NEW_CHANNEL)
    return client


async def test_joining_the_hub_creates_a_channel_and_moves_the_member_in(engine: Engine, client: RecordingClient) -> None:
    seed(engine, AutoChannelHub(id=GUILD_ID, channel_id=HUB_ID), AutoChannelSettings(id=MEMBER_ID, user_limit=4))

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
    assert [(channel.owner_id, channel.id) for channel in _channels(engine)] == [(MEMBER_ID, 60)]


async def test_an_owner_rejoining_the_hub_is_moved_to_their_channel(engine: Engine, client: RecordingClient) -> None:
    seed(
        engine,
        AutoChannelHub(id=GUILD_ID, channel_id=HUB_ID),
        AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID),
    )

    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    assert client.requests_to("POST", f"/guilds/{GUILD_ID}/channels") == []
    assert client.requests_to("PATCH", f"/guilds/{GUILD_ID}/members/{MEMBER_ID}")[0].json == {"channel_id": "60"}


async def test_the_guild_limit_stops_new_channels(engine: Engine, client: RecordingClient) -> None:
    seed(
        engine,
        AutoChannelHub(id=GUILD_ID, channel_id=HUB_ID, max_channels=1),
        AutoChannel(id=61, guild_id=GUILD_ID, owner_id=99),
    )
    client.reply("POST", "/users/@me/channels", {"id": "7", "type": 1})
    client.reply("POST", "/channels/7/messages", MESSAGE_JSON)

    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    assert client.requests_to("POST", f"/guilds/{GUILD_ID}/channels") == []
    assert "as many automatic channels as it allows" in client.requests_to("POST", "/channels/7/messages")[0].json["content"]


async def test_leaving_an_empty_channel_deletes_it(engine: Engine, client: RecordingClient) -> None:
    seed(engine, AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID))
    cog = _cog(engine, client)
    cog.voice.move(Snowflake(GUILD_ID), Snowflake(MEMBER_ID), Snowflake(60))
    cog.voice.move(Snowflake(GUILD_ID), Snowflake(4), Snowflake(60))

    await cog.on_voice_state_update(_state(client, None))
    assert client.requests_to("DELETE", "/channels/60") == []  # someone is still in it

    await cog.on_voice_state_update(_state(client, None, user_id=4))
    assert len(client.requests_to("DELETE", "/channels/60")) == 1
    assert _channels(engine) == []


async def test_guild_create_cleans_up_channels_emptied_while_offline(engine: Engine, client: RecordingClient) -> None:
    seed(
        engine,
        AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID),
        AutoChannel(id=61, guild_id=GUILD_ID, owner_id=4),
    )
    voice_state = {
        key: value for key, value in _state(client, 61, user_id=4).model.model_dump(mode="json").items() if key != "member"
    }
    guild = bind(client, parse_dispatch(EventName.GUILD_CREATE, {**GUILD_JSON, "voice_states": [voice_state]}))
    assert isinstance(guild, Guild)

    cog = _cog(engine, client)
    await cog.on_guild_create(guild)

    guild_id = Snowflake(GUILD_ID)
    assert (cog.voice.occupied(guild_id, Snowflake(61)), cog.voice.occupied(guild_id, Snowflake(60))) == (True, False)
    assert [sent.path for sent in client.sent if sent.method == "DELETE"] == ["/channels/60"]
    assert [channel.id for channel in _channels(engine)] == [61]


async def test_limit_is_saved_and_applied_to_the_owned_channel(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    seed(engine, AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID))
    discord_client.reply("PATCH", "/channels/60", NEW_CHANNEL)
    interaction = make_interaction(
        "autochannel",
        options=[InteractionDataOption(name="limit", type=4, value=5)],
        guild_id=GUILD_ID,
    )

    await AutoChannels.set_limit.invoke(_cog(engine, discord_client), interaction, interaction.options)

    assert discord_client.requests_to("PATCH", "/channels/60")[0].json == {"user_limit": 5}
    with Session(engine) as session:
        assert session.exec(alive(AutoChannelSettings)).one().user_limit == 5


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


async def test_a_failed_move_to_their_channel_keeps_it(engine: Engine, client: RecordingClient) -> None:
    seed(
        engine,
        AutoChannelHub(id=GUILD_ID, channel_id=HUB_ID),
        AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID),
    )
    not_in_voice = {"code": 40032, "message": "Target user is not connected to voice."}
    client.reply("PATCH", f"/guilds/{GUILD_ID}/members/{MEMBER_ID}", not_in_voice, status=400)
    client.reply("GET", "/channels/60", NEW_CHANNEL)

    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    assert client.requests_to("POST", f"/guilds/{GUILD_ID}/channels") == []
    assert client.requests_to("DELETE", "/channels/60") == []
    assert [channel.id for channel in _channels(engine)] == [60]


async def test_an_empty_channel_that_cant_be_deleted_is_kept_to_retry(engine: Engine, client: RecordingClient) -> None:
    seed(engine, AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID))
    client.reply("DELETE", "/channels/60", {"code": 50001, "message": "Missing Access"}, status=403)
    cog = _cog(engine, client)
    cog.voice.move(Snowflake(GUILD_ID), Snowflake(MEMBER_ID), Snowflake(60))

    await cog.on_voice_state_update(_state(client, None))

    assert len(client.requests_to("DELETE", "/channels/60")) == 1
    assert [channel.id for channel in _channels(engine)] == [60]


async def test_an_owner_whose_channel_was_deleted_by_hand_gets_a_new_one(engine: Engine, client: RecordingClient) -> None:
    seed(
        engine,
        AutoChannelHub(id=GUILD_ID, channel_id=HUB_ID),
        AutoChannel(id=61, guild_id=GUILD_ID, owner_id=MEMBER_ID),
    )
    invalid = {"code": 50035, "message": "Invalid Form Body"}
    client.reply("PATCH", f"/guilds/{GUILD_ID}/members/{MEMBER_ID}", invalid, status=400)
    client.reply("GET", "/channels/61", {"code": 10003, "message": "Unknown Channel"}, status=404)

    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    assert client.requests_to("DELETE", "/channels/61") == []  # it's gone: just forget it
    assert len(client.requests_to("POST", f"/guilds/{GUILD_ID}/channels")) == 1
    assert 61 not in [channel.id for channel in _channels(engine)]


async def test_marking_a_channel_restores_a_soft_deleted_hub(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    seed(
        engine,
        AutoChannelHub(id=GUILD_ID, channel_id=HUB_ID, max_channels=5, deleted_at=datetime(2026, 1, 1, tzinfo=UTC)),
        AutoChannel(id=61, guild_id=GUILD_ID, owner_id=99),
    )
    discord_client.reply("POST", "/users/@me/channels", {"id": "7", "type": 1})
    discord_client.reply("POST", "/channels/7/messages", MESSAGE_JSON)
    new_hub = ChannelModel.model_validate({"id": "51", "type": 2, "name": "Join me"})
    cog = _cog(engine, discord_client)
    mark = make_interaction(
        "autochannel",
        options=[InteractionDataOption(name="channel", type=7, value="51")],
        resolved=ResolvedData(channels={"51": new_hub}),
        guild_id=GUILD_ID,
        permissions=Permissions.MANAGE_GUILD,
    )
    limit = make_interaction(
        "autochannel",
        options=[InteractionDataOption(name="limit", type=4, value=1)],
        guild_id=GUILD_ID,
        permissions=Permissions.MANAGE_GUILD,
    )

    await AutoChannels.mark.invoke(cog, mark, mark.options)
    await AutoChannels.guild_limit.invoke(cog, limit, limit.options)
    await cog.on_voice_state_update(_state(discord_client, 51))

    assert "now allows at most 1 at once" in discord_client.interaction_responses()[1]["data"]["embeds"][0]["description"]
    assert discord_client.requests_to("POST", f"/guilds/{GUILD_ID}/channels") == []
    assert "as many automatic channels" in discord_client.requests_to("POST", "/channels/7/messages")[0].json["content"]


async def test_naming_restores_soft_deleted_settings_with_the_limit_reset(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
    client: RecordingClient,
) -> None:
    deleted = AutoChannelSettings(id=MEMBER_ID, name="old", user_limit=4, deleted_at=datetime(2026, 1, 1, tzinfo=UTC))
    seed(engine, AutoChannelHub(id=GUILD_ID, channel_id=HUB_ID), deleted)
    interaction = make_interaction(
        "autochannel",
        options=[InteractionDataOption(name="name", type=3, value="Den")],
        guild_id=GUILD_ID,
    )

    await AutoChannels.set_name.invoke(_cog(engine, discord_client), interaction, interaction.options)
    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    (create,) = client.requests_to("POST", f"/guilds/{GUILD_ID}/channels")
    assert (create.json["name"], create.json["user_limit"]) == ("Den", 0)


async def test_a_soft_deleted_channel_does_not_count_toward_the_guild_limit(engine: Engine, client: RecordingClient) -> None:
    seed(
        engine,
        AutoChannelHub(id=GUILD_ID, channel_id=HUB_ID, max_channels=1),
        AutoChannel(id=61, guild_id=GUILD_ID, owner_id=99, deleted_at=datetime(2026, 1, 1, tzinfo=UTC)),
    )

    await _cog(engine, client).on_voice_state_update(_state(client, HUB_ID))

    assert len(client.requests_to("POST", f"/guilds/{GUILD_ID}/channels")) == 1
    assert [channel.id for channel in _channels(engine)] == [60]
