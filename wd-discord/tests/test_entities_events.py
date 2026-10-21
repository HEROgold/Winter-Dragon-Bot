"""Unit tests: :func:`wd_discord.entities.bind` wraps each parsed dispatch event in its client-bound entity."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeAliasType, get_args

from wd_discord import (
    Channel,
    ChannelPinsUpdate,
    CurrentUser,
    Guild,
    GuildDelete,
    Member,
    MemberRemove,
    MembersChunk,
    Message,
    PartialChannel,
    PartialGuild,
    PartialMember,
    PartialRole,
    PartialUser,
    Presence,
    Ready,
    Role,
    ThreadCreate,
    ThreadDelete,
    ThreadListSync,
    ThreadMember,
    ThreadMembersUpdate,
    VoiceChannelStartTimeUpdate,
    VoiceChannelStatusUpdate,
    VoiceState,
    bind,
)
from wd_discord.entities import event_entities
from wd_discord.entities.base import Entity, Partial
from wd_discord.gateway import EventName, RawEvent, Status, parse_dispatch, parse_ready
from wd_discord.gateway.events import GuildMemberUpdate
from wd_discord.permissions import ChannelType
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
VOICE_STATE_JSON = {
    "guild_id": "7",
    "channel_id": "5",
    "user_id": "3",
    "session_id": "s",
    "deaf": False,
    "mute": False,
    "self_deaf": False,
    "self_mute": True,
    "self_video": False,
    "suppress": False,
    "request_to_speak_timestamp": None,
}
MEMBER_JSON = {
    "user": {"id": "3", "username": "someone", "discriminator": "0"},
    "roles": [],
    "joined_at": None,
    "deaf": False,
    "mute": False,
}


CHANNEL_JSON = {"id": "5", "type": 0, "guild_id": "7", "name": "general"}
THREAD_JSON = {"id": "6", "type": 11, "guild_id": "7", "parent_id": "5", "name": "a thread"}
THREAD_MEMBER_JSON = {"id": "6", "user_id": "3", "join_timestamp": "2026-10-10T12:00:00+00:00", "flags": 0}
ROLE_JSON = {
    "id": "8",
    "name": "mods",
    "color": 0,
    "hoist": False,
    "position": 1,
    "permissions": "0",
    "managed": False,
    "mentionable": True,
    "flags": 0,
}
PRESENCE_JSON = {
    "user": {"id": "3"},
    "status": "idle",
    "activities": [{"name": "Custom Status", "type": 4, "created_at": 1, "state": "afk", "emoji": {"name": "zzz"}}],
    "client_status": {"desktop": "idle"},
}
GUILD_EVENT_SAMPLES = {
    EventName.GUILD_UPDATE: GUILD_JSON,
    EventName.GUILD_DELETE: {"id": "7", "unavailable": True},
    EventName.CHANNEL_CREATE: CHANNEL_JSON,
    EventName.CHANNEL_UPDATE: CHANNEL_JSON,
    EventName.CHANNEL_DELETE: CHANNEL_JSON,
    EventName.CHANNEL_PINS_UPDATE: {"guild_id": "7", "channel_id": "5", "last_pin_timestamp": "2026-10-10T12:00:00+00:00"},
    EventName.THREAD_CREATE: {**THREAD_JSON, "newly_created": True},
    EventName.THREAD_UPDATE: THREAD_JSON,
    EventName.THREAD_DELETE: {"id": "6", "guild_id": "7", "parent_id": "5", "type": 11},
    EventName.THREAD_LIST_SYNC: {"guild_id": "7", "threads": [THREAD_JSON], "members": [THREAD_MEMBER_JSON]},
    EventName.THREAD_MEMBER_UPDATE: {**THREAD_MEMBER_JSON, "guild_id": "7"},
    EventName.THREAD_MEMBERS_UPDATE: {
        "id": "6",
        "guild_id": "7",
        "member_count": 2,
        "added_members": [{**THREAD_MEMBER_JSON, "member": MEMBER_JSON, "presence": None}],
        "removed_member_ids": ["4"],
    },
    EventName.VOICE_CHANNEL_STATUS_UPDATE: {"id": "5", "guild_id": "7", "status": "chilling"},
    EventName.VOICE_CHANNEL_START_TIME_UPDATE: {"id": "5", "guild_id": "7", "voice_start_time": 1_760_097_600},
    EventName.GUILD_MEMBER_ADD: {**MEMBER_JSON, "guild_id": "7"},
    EventName.GUILD_MEMBER_REMOVE: {"guild_id": "7", "user": MEMBER_JSON["user"]},
    EventName.GUILD_MEMBERS_CHUNK: {
        "guild_id": "7",
        "members": [MEMBER_JSON],
        "chunk_index": 0,
        "chunk_count": 1,
        "not_found": ["4"],
        "presences": [PRESENCE_JSON],
        "nonce": "n",
    },
    EventName.GUILD_ROLE_CREATE: {"guild_id": "7", "role": ROLE_JSON},
    EventName.GUILD_ROLE_UPDATE: {"guild_id": "7", "role": ROLE_JSON},
    EventName.GUILD_ROLE_DELETE: {"guild_id": "7", "role_id": "8"},
    EventName.USER_UPDATE: {"id": "42", "username": "bot", "discriminator": "0"},
    EventName.PRESENCE_UPDATE: {**PRESENCE_JSON, "guild_id": "7"},
}
"""A payload for each guild, channel and thread event, as the gateway sends it."""


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


def test_bind_voice_state_update() -> None:
    client = RecordingClient()
    state = bind(client, parse_dispatch(EventName.VOICE_STATE_UPDATE, VOICE_STATE_JSON))
    assert isinstance(state, VoiceState)
    assert state.channel == PartialChannel(client, Snowflake(5))
    assert state.member == PartialMember(client, Snowflake(3), Snowflake(7))


def test_voice_state_member_is_full_when_sent() -> None:
    state = bind(RecordingClient(), parse_dispatch(EventName.VOICE_STATE_UPDATE, {**VOICE_STATE_JSON, "member": MEMBER_JSON}))
    assert isinstance(state, VoiceState)
    assert isinstance(state.member, Member)
    assert state.member.guild_id == Snowflake(7)


def test_voice_state_disconnect_has_no_channel() -> None:
    state = bind(RecordingClient(), parse_dispatch(EventName.VOICE_STATE_UPDATE, {**VOICE_STATE_JSON, "channel_id": None}))
    assert isinstance(state, VoiceState)
    assert state.channel is None


def test_bind_returns_events_without_an_entity_unchanged() -> None:
    raw = parse_dispatch(EventName.WEBHOOKS_UPDATE, {"channel_id": "2"})
    assert isinstance(raw, RawEvent)
    assert bind(RecordingClient(), raw) is raw


def test_event_entities_match_what_bind_returns() -> None:
    samples = {
        EventName.READY: parse_ready(READY_JSON),
        EventName.MESSAGE_CREATE: parse_dispatch(EventName.MESSAGE_CREATE, MESSAGE_JSON),
        EventName.GUILD_CREATE: parse_dispatch(EventName.GUILD_CREATE, GUILD_JSON),
        EventName.INTERACTION_CREATE: parse_dispatch(EventName.INTERACTION_CREATE, INTERACTION_JSON),
        EventName.VOICE_STATE_UPDATE: parse_dispatch(EventName.VOICE_STATE_UPDATE, VOICE_STATE_JSON),
        **{event: parse_dispatch(event, data) for event, data in GUILD_EVENT_SAMPLES.items()},
    }
    entities = event_entities()
    assert entities.keys() == samples.keys()
    for event, model in samples.items():
        entity = entities[event]
        expected = entity.__value__ if isinstance(entity, TypeAliasType) else entity
        assert isinstance(bind(RecordingClient(), model), expected), event


def test_event_entities_are_entities_or_partials() -> None:
    """``EntityType`` can't constrain a ``type`` alias's members, so check them here."""
    for event, entity in event_entities().items():
        members = get_args(entity.__value__) if isinstance(entity, TypeAliasType) else (entity,)
        for member in members:
            assert issubclass(member, Entity | Partial), (event, member)


def bound(event: EventName) -> object:
    """Parse and bind the sample payload of ``event``."""
    return bind(RecordingClient(), parse_dispatch(event, GUILD_EVENT_SAMPLES[event]))


def test_channel_events_bind_to_the_channel() -> None:
    for event in (EventName.CHANNEL_CREATE, EventName.CHANNEL_UPDATE, EventName.CHANNEL_DELETE, EventName.THREAD_UPDATE):
        channel = bound(event)
        assert isinstance(channel, Channel), event
        assert channel.guild == PartialGuild(channel.client, Snowflake(7))


def test_guild_update_binds_to_the_guild() -> None:
    guild = bound(EventName.GUILD_UPDATE)
    assert isinstance(guild, Guild)
    assert guild.name == "My Guild"


def test_guild_delete_tells_an_outage_from_leaving() -> None:
    outage = bound(EventName.GUILD_DELETE)
    assert isinstance(outage, GuildDelete)
    assert outage.unavailable
    assert outage.guild.id == Snowflake(7)

    left = bind(RecordingClient(), parse_dispatch(EventName.GUILD_DELETE, {"id": "7"}))
    assert isinstance(left, GuildDelete)
    assert not left.unavailable


def test_channel_pins_update() -> None:
    pins = bound(EventName.CHANNEL_PINS_UPDATE)
    assert isinstance(pins, ChannelPinsUpdate)
    assert pins.channel.id == Snowflake(5)
    assert pins.guild is not None
    assert pins.guild.id == Snowflake(7)
    assert pins.last_pin_timestamp == datetime(2026, 10, 10, 12, tzinfo=UTC)


def test_thread_create_says_whether_the_thread_is_new() -> None:
    created = bound(EventName.THREAD_CREATE)
    assert isinstance(created, ThreadCreate)
    assert created.newly_created
    assert created.thread.id == Snowflake(6)


def test_thread_delete() -> None:
    deleted = bound(EventName.THREAD_DELETE)
    assert isinstance(deleted, ThreadDelete)
    assert deleted.thread.id == Snowflake(6)
    assert deleted.parent is not None
    assert deleted.parent.id == Snowflake(5)
    assert deleted.type is ChannelType.PUBLIC_THREAD


def test_thread_list_sync_of_the_whole_guild_names_no_channels() -> None:
    sync = bound(EventName.THREAD_LIST_SYNC)
    assert isinstance(sync, ThreadListSync)
    assert sync.channels is None
    assert [thread.id for thread in sync.threads] == [Snowflake(6)]
    assert [member.thread.id for member in sync.members] == [Snowflake(6)]


def test_thread_member_update_binds_to_the_membership() -> None:
    member = bound(EventName.THREAD_MEMBER_UPDATE)
    assert isinstance(member, ThreadMember)
    assert member.thread.id == Snowflake(6)


def test_thread_members_update_lists_who_joined_and_left() -> None:
    update = bound(EventName.THREAD_MEMBERS_UPDATE)
    assert isinstance(update, ThreadMembersUpdate)
    assert [member.id for member in update.added_members] == [Snowflake(3)]
    assert [member.id for member in update.removed_members] == [Snowflake(4)]
    assert update.member_count == 2


def test_voice_channel_status_update() -> None:
    update = bound(EventName.VOICE_CHANNEL_STATUS_UPDATE)
    assert isinstance(update, VoiceChannelStatusUpdate)
    assert update.channel.id == Snowflake(5)
    assert update.status == "chilling"


def test_voice_channel_start_time_is_a_datetime() -> None:
    update = bound(EventName.VOICE_CHANNEL_START_TIME_UPDATE)
    assert isinstance(update, VoiceChannelStartTimeUpdate)
    assert update.voice_start_time == datetime(2025, 10, 10, 12, tzinfo=UTC)


def test_member_add_binds_to_the_member() -> None:
    member = bound(EventName.GUILD_MEMBER_ADD)
    assert isinstance(member, Member)
    assert member.guild_id == Snowflake(7)


def test_member_remove_says_who_left_which_guild() -> None:
    removed = bound(EventName.GUILD_MEMBER_REMOVE)
    assert isinstance(removed, MemberRemove)
    assert removed.user.id == Snowflake(3)
    assert removed.guild.id == Snowflake(7)


def test_members_chunk() -> None:
    chunk = bound(EventName.GUILD_MEMBERS_CHUNK)
    assert isinstance(chunk, MembersChunk)
    assert [member.id for member in chunk.members] == [Snowflake(3)]
    assert list(chunk.not_found) == [PartialUser(chunk.client, Snowflake(4))]
    assert [presence.status for presence in chunk.presences] == [Status.idle]
    assert (chunk.chunk_index, chunk.chunk_count, chunk.nonce) == (0, 1, "n")


def test_role_events_bind_to_the_role() -> None:
    for event in (EventName.GUILD_ROLE_CREATE, EventName.GUILD_ROLE_UPDATE):
        role = bound(event)
        assert isinstance(role, Role), event
        assert role.name == "mods"
        assert role.guild_id == Snowflake(7)


def test_role_delete_binds_to_a_handle_on_the_role() -> None:
    role = bound(EventName.GUILD_ROLE_DELETE)
    assert isinstance(role, PartialRole)
    assert role == PartialRole(role.client, Snowflake(8), Snowflake(7))


def test_user_update_binds_to_the_current_user() -> None:
    user = bound(EventName.USER_UPDATE)
    assert isinstance(user, CurrentUser)
    assert user.username == "bot"


def test_presence_update() -> None:
    presence = bound(EventName.PRESENCE_UPDATE)
    assert isinstance(presence, Presence)
    assert presence.status is Status.idle
    assert presence.member == PartialMember(presence.client, Snowflake(3), Snowflake(7))
    [custom] = presence.activities
    assert custom.state == "afk"
    assert presence.client_status.desktop is Status.idle


def test_member_update_waits_for_the_state_cache() -> None:
    """A partial member can't become a Member until the state cache merges it, so it stays a model."""
    data = {**MEMBER_JSON, "guild_id": "7", "avatar": None, "banner": None}
    del data["deaf"], data["mute"]
    update = parse_dispatch(EventName.GUILD_MEMBER_UPDATE, data)
    assert isinstance(update, GuildMemberUpdate)
    assert update.deaf is None
    assert bind(RecordingClient(), update) is update
