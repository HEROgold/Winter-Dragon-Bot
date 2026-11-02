"""Unit tests: voice channels a cog records, deleted once empty (no network)."""

from typing import TYPE_CHECKING

from herogold.log import getLogger
from sqlmodel import Session
from wd_db.extension.lifecycle import alive
from wd_db.testing import seed
from wd_discord.snowflake import Snowflake
from wd_discord.testing import RecordingClient

from winter_dragon.cogs.autochannel import AutoChannel
from winter_dragon.voice_channels import EmptiedChannels, VoiceOccupancy


if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import Engine


GUILD_ID = 1
OTHER_GUILD_ID = 2
MEMBER_ID = 3
OTHER_MEMBER_ID = 4
CHANNEL_JSON = {"id": "60", "type": 2, "guild_id": "1", "name": "asker's channel"}


def _client(delete_status: int = 200) -> RecordingClient:
    client = RecordingClient()
    client.reply("DELETE", "/channels/60", CHANNEL_JSON, status=delete_status)
    return client


def _emptied(
    engine: Engine, client: RecordingClient, on_forgotten: Callable[[Session, AutoChannel], None] | None = None
) -> EmptiedChannels[AutoChannel]:
    return EmptiedChannels(AutoChannel, engine, client, getLogger("test"), "Automatic channel is empty", on_forgotten)


def _ids(engine: Engine) -> list[int]:
    with Session(engine) as session:
        return sorted(channel.id for channel in session.exec(alive(AutoChannel)))


async def test_left_deletes_a_recorded_channel_once_empty_and_forgets_it(engine: Engine) -> None:
    seed(engine, AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID))
    client = _client()
    channels = _emptied(engine, client)
    voice = VoiceOccupancy()
    guild_id = Snowflake(GUILD_ID)
    voice.move(guild_id, Snowflake(MEMBER_ID), Snowflake(60))
    voice.move(guild_id, Snowflake(OTHER_MEMBER_ID), Snowflake(60))

    voice.move(guild_id, Snowflake(MEMBER_ID), None)
    await channels.left(voice, guild_id, Snowflake(60), None)
    assert client.requests_to("DELETE", "/channels/60") == []  # someone is still in it

    voice.move(guild_id, Snowflake(OTHER_MEMBER_ID), None)
    await channels.left(voice, guild_id, Snowflake(60), None)
    assert len(client.requests_to("DELETE", "/channels/60")) == 1
    assert _ids(engine) == []


async def test_left_ignores_a_channel_without_a_row(engine: Engine) -> None:
    client = _client()
    channels = _emptied(engine, client)
    guild_id = Snowflake(GUILD_ID)

    await channels.left(VoiceOccupancy(), guild_id, Snowflake(70), None)

    assert client.requests_to("DELETE", "/channels/70") == []


async def test_a_channel_discord_refuses_to_delete_keeps_its_row(engine: Engine) -> None:
    seed(engine, AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID))
    client = _client(delete_status=403)
    channels = _emptied(engine, client)

    await channels.left(VoiceOccupancy(), Snowflake(GUILD_ID), Snowflake(60), None)

    assert len(client.requests_to("DELETE", "/channels/60")) == 1
    assert _ids(engine) == [60]


async def test_sweep_deletes_only_the_unoccupied_channels_of_its_guild(engine: Engine) -> None:
    seed(
        engine,
        AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID),
        AutoChannel(id=61, guild_id=GUILD_ID, owner_id=OTHER_MEMBER_ID),
        AutoChannel(id=62, guild_id=OTHER_GUILD_ID, owner_id=MEMBER_ID),
    )
    client = _client()
    channels = _emptied(engine, client)
    voice = VoiceOccupancy()
    voice.move(Snowflake(GUILD_ID), Snowflake(OTHER_MEMBER_ID), Snowflake(61))

    await channels.sweep(voice, Snowflake(GUILD_ID))

    assert [sent.path for sent in client.sent if sent.method == "DELETE"] == ["/channels/60"]
    assert _ids(engine) == [61, 62]


async def test_on_forgotten_is_called_once_with_the_row(engine: Engine) -> None:
    seed(engine, AutoChannel(id=60, guild_id=GUILD_ID, owner_id=MEMBER_ID))
    forgotten: list[tuple[bool, int]] = []

    def on_forgotten(session: Session, row: AutoChannel) -> None:
        forgotten.append((isinstance(session, Session), row.id))

    channels = _emptied(engine, _client(), on_forgotten)

    await channels.left(VoiceOccupancy(), Snowflake(GUILD_ID), Snowflake(60), None)

    assert forgotten == [(True, 60)]
