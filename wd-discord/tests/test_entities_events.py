"""Unit tests: :func:`wd_discord.entities.bind` wraps each parsed dispatch event in its client-bound entity."""

from __future__ import annotations

from typing import TypeAliasType

from wd_discord import CurrentUser, Guild, Message, PartialGuild, Ready, bind
from wd_discord.entities import event_entities
from wd_discord.gateway import EventName, RawEvent, parse_dispatch, parse_ready
from wd_discord.snowflake import Snowflake
from wd_discord.testing import GUILD_JSON, RecordingClient


MESSAGE_JSON = {
    "id": "1",
    "channel_id": "2",
    "author": {"id": "3", "username": "someone", "discriminator": "0"},
    "content": "hi",
    "timestamp": "t",
    "tts": False,
    "mention_everyone": False,
}
READY_JSON = {
    "session_id": "s",
    "resume_gateway_url": "wss://x",
    "user": {"id": "42", "username": "bot", "discriminator": "0"},
    "guilds": [{"id": "7", "unavailable": True}, {"id": "8", "unavailable": True}],
    "shard": [0, 2],
}
INTERACTION_JSON = {"id": "1", "application_id": "2", "type": 1, "token": "tok", "version": 1}


def test_bind_message_create() -> None:
    client = RecordingClient()
    message = bind(client, parse_dispatch(EventName.MESSAGE_CREATE, MESSAGE_JSON))
    assert isinstance(message, Message)
    assert message.client is client
    assert message.channel.id == Snowflake(2)


def test_bind_guild_create() -> None:
    guild = bind(RecordingClient(), parse_dispatch(EventName.GUILD_CREATE, GUILD_JSON))
    assert isinstance(guild, Guild)
    assert guild.name == "My Guild"


def test_bind_ready() -> None:
    client = RecordingClient()
    ready = bind(client, parse_ready(READY_JSON))
    assert isinstance(ready, Ready)
    assert isinstance(ready.user, CurrentUser)
    assert ready.user.username == "bot"
    assert list(ready.guilds) == [PartialGuild(client, Snowflake(7)), PartialGuild(client, Snowflake(8))]
    assert ready.shard == (0, 2)
    assert ready.session_id == "s"


def test_bind_returns_events_without_an_entity_unchanged() -> None:
    raw = parse_dispatch(EventName.TYPING_START, {"channel_id": "2"})
    assert isinstance(raw, RawEvent)
    assert bind(RecordingClient(), raw) is raw


def test_event_entities_match_what_bind_returns() -> None:
    samples = {
        EventName.READY: parse_ready(READY_JSON),
        EventName.MESSAGE_CREATE: parse_dispatch(EventName.MESSAGE_CREATE, MESSAGE_JSON),
        EventName.GUILD_CREATE: parse_dispatch(EventName.GUILD_CREATE, GUILD_JSON),
        EventName.INTERACTION_CREATE: parse_dispatch(EventName.INTERACTION_CREATE, INTERACTION_JSON),
    }
    entities = event_entities()
    assert entities.keys() == samples.keys()
    for event, model in samples.items():
        entity = entities[event]
        expected = entity.__value__ if isinstance(entity, TypeAliasType) else entity
        assert isinstance(bind(RecordingClient(), model), expected), event
