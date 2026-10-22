"""Unit tests: :class:`wd_discord.cache.StateCache` follows the gateway, and :meth:`Client.receive` feeds it."""

from typing import Any

from wd_discord import Channel, MemberRemove, Role
from wd_discord.cache import StateCache
from wd_discord.gateway import EventName, parse_dispatch, parse_ready
from wd_discord.gateway.connection import ALL_MEMBERS_NONCE
from wd_discord.snowflake import Snowflake
from wd_discord.testing import (
    GUILD_JSON,
    RecordingClient,
    channel_json,
    guild_create_json,
    member_json,
    role_json,
    thread_json,
    user_json,
    voice_state_json,
)


GUILD = Snowflake(7)


def ready_cache() -> StateCache:
    """Return a cache that received GUILD_CREATE for guild 7."""
    cache = StateCache()
    cache.apply(parse_dispatch(EventName.GUILD_CREATE, guild_create_json()))
    return cache


def apply(cache: StateCache, event: EventName, data: dict[str, Any]) -> object:
    return cache.apply(parse_dispatch(event, data))


def test_guild_create_lays_down_the_guild() -> None:
    state = ready_cache().guild(GUILD)
    assert state is not None
    assert state.guild.name == "My Guild"
    assert state.channels is not None
    assert state.channels[Snowflake(5)].guild_id == GUILD
    assert state.threads is not None
    assert list(state.threads) == [Snowflake(6)]
    assert list(state.roles) == [Snowflake(8)]
    assert list(state.members) == [Snowflake(3)]
    assert state.members_complete
    assert state.voice_states is not None
    assert state.voice_states[Snowflake(3)].guild_id == GUILD


def test_the_guild_keeps_no_stale_copy_of_its_lists() -> None:
    state = ready_cache().guild(GUILD)
    assert state is not None
    assert state.guild.model_dump().get("members") == []


def test_a_large_guild_has_incomplete_members() -> None:
    cache = StateCache()
    cache.apply(parse_dispatch(EventName.GUILD_CREATE, guild_create_json(large=True)))
    state = cache.guild(GUILD)
    assert state is not None
    assert not state.members_complete


def test_the_last_chunk_of_the_full_member_request_completes_the_members() -> None:
    cache = StateCache()
    cache.apply(parse_dispatch(EventName.GUILD_CREATE, {**GUILD_CREATE, "large": True}))
    chunk = {"guild_id": "7", "members": [MEMBER], "chunk_index": 0, "chunk_count": 2, "nonce": ALL_MEMBERS_NONCE}
    state = cache.guild(GUILD)
    assert state is not None

    apply(cache, EventName.GUILD_MEMBERS_CHUNK, chunk)
    assert not state.members_complete
    apply(cache, EventName.GUILD_MEMBERS_CHUNK, {**chunk, "chunk_index": 1})
    assert state.members_complete


def test_chunks_of_another_request_leave_the_members_incomplete() -> None:
    cache = StateCache()
    cache.apply(parse_dispatch(EventName.GUILD_CREATE, {**GUILD_CREATE, "large": True}))
    apply(cache, EventName.GUILD_MEMBERS_CHUNK, {"guild_id": "7", "members": [MEMBER], "chunk_index": 0, "chunk_count": 1})
    state = cache.guild(GUILD)
    assert state is not None
    assert not state.members_complete


def test_channel_lookup_covers_channels_threads_and_dms() -> None:
    cache = ready_cache()
    apply(cache, EventName.CHANNEL_CREATE, {"id": "9", "type": 1})
    assert cache.channel(Snowflake(5)) is not None
    assert cache.channel(Snowflake(6)) is not None
    assert cache.channel(Snowflake(9)) is not None
    assert cache.channel(Snowflake(404)) is None


def test_channel_update_returns_the_channel_it_replaced() -> None:
    cache = ready_cache()
    previous = apply(cache, EventName.CHANNEL_UPDATE, channel_json(name="renamed"))
    assert previous is not None
    assert previous.name == "general"  # type: ignore[attr-defined]
    channel = cache.channel(Snowflake(5))
    assert channel is not None
    assert channel.name == "renamed"


def test_channel_delete_forgets_it() -> None:
    cache = ready_cache()
    removed = apply(cache, EventName.CHANNEL_DELETE, channel_json())
    assert removed is not None
    assert cache.channel(Snowflake(5)) is None


def test_thread_delete_forgets_it() -> None:
    cache = ready_cache()
    apply(cache, EventName.THREAD_DELETE, {"id": "6", "guild_id": "7", "parent_id": "5", "type": 11})
    assert cache.channel(Snowflake(6)) is None


def test_thread_list_sync_replaces_the_synced_channels_threads() -> None:
    cache = ready_cache()
    fresh = thread_json(id="10")
    apply(cache, EventName.THREAD_LIST_SYNC, {"guild_id": "7", "channel_ids": ["5"], "threads": [fresh], "members": []})
    assert cache.channel(Snowflake(6)) is None
    assert cache.channel(Snowflake(10)) is not None


def test_pins_update_moves_the_last_pin() -> None:
    cache = ready_cache()
    apply(
        cache,
        EventName.CHANNEL_PINS_UPDATE,
        {"guild_id": "7", "channel_id": "5", "last_pin_timestamp": "2026-10-10T12:00:00+00:00"},
    )
    channel = cache.channel(Snowflake(5))
    assert channel is not None
    assert channel.last_pin_timestamp is not None


def test_guild_delete_while_unavailable_keeps_the_data() -> None:
    cache = ready_cache()
    apply(cache, EventName.GUILD_DELETE, {"id": "7", "unavailable": True})
    state = cache.guild(GUILD)
    assert state is not None
    assert state.unavailable


def test_guild_delete_after_leaving_forgets_the_guild_and_its_channels() -> None:
    cache = ready_cache()
    apply(cache, EventName.GUILD_DELETE, {"id": "7"})
    assert cache.guild(GUILD) is None
    assert cache.channel(Snowflake(5)) is None


def test_guild_update_replaces_the_guild_and_its_roles() -> None:
    cache = ready_cache()
    previous = apply(cache, EventName.GUILD_UPDATE, {**GUILD_JSON, "id": "7", "name": "Renamed", "roles": []})
    assert previous is not None
    state = cache.guild(GUILD)
    assert state is not None
    assert state.guild.name == "Renamed"
    assert state.roles == {}


def test_member_add_and_remove() -> None:
    cache = ready_cache()
    apply(cache, EventName.GUILD_MEMBER_ADD, member_json(roles=["8"], user=user_json(id="4"), guild_id="7"))
    state = cache.guild(GUILD)
    assert state is not None
    assert Snowflake(4) in state.members
    apply(cache, EventName.GUILD_MEMBER_REMOVE, {"guild_id": "7", "user": user_json(id="4")})
    assert Snowflake(4) not in state.members


def test_member_update_merges_into_the_cached_member() -> None:
    cache = ready_cache()
    update = member_json(guild_id="7", nick="nick", avatar=None, banner=None)
    previous = apply(cache, EventName.GUILD_MEMBER_UPDATE, update)
    assert previous is not None
    state = cache.guild(GUILD)
    assert state is not None
    member = state.members[Snowflake(3)]
    assert member.nick == "nick"
    assert member.roles == []
    assert member.deaf is False  # kept from the cached member; the update didn't send it


def test_member_update_of_an_unknown_member_is_ignored() -> None:
    cache = ready_cache()
    stranger = user_json(id="99")
    update = {"guild_id": "7", "user": stranger, "roles": [], "avatar": None, "banner": None, "joined_at": None}
    assert apply(cache, EventName.GUILD_MEMBER_UPDATE, update) is None
    state = cache.guild(GUILD)
    assert state is not None
    assert Snowflake(99) not in state.members


def test_role_delete_takes_the_role_off_its_members() -> None:
    cache = ready_cache()
    removed = apply(cache, EventName.GUILD_ROLE_DELETE, {"guild_id": "7", "role_id": "8"})
    assert removed is not None
    state = cache.guild(GUILD)
    assert state is not None
    assert state.roles == {}
    assert state.members[Snowflake(3)].roles == []


def test_role_update_returns_the_role_it_replaced() -> None:
    cache = ready_cache()
    previous = apply(cache, EventName.GUILD_ROLE_UPDATE, {"guild_id": "7", "role": role_json(name="admins")})
    assert previous is not None
    assert previous.name == "mods"  # type: ignore[attr-defined]


def test_voice_state_follows_joins_and_leaves() -> None:
    cache = ready_cache()
    state = cache.guild(GUILD)
    assert state is not None
    assert state.voice_states is not None
    apply(cache, EventName.VOICE_STATE_UPDATE, voice_state_json(guild_id="7", channel_id=None))
    assert Snowflake(3) not in state.voice_states
    apply(cache, EventName.VOICE_STATE_UPDATE, voice_state_json(guild_id="7", member=member_json(roles=["8"], nick="in voice")))
    assert Snowflake(3) in state.voice_states
    assert state.members[Snowflake(3)].nick == "in voice"


def test_ready_and_user_update_track_the_bot() -> None:
    cache = StateCache()
    cache.apply(
        parse_ready({"v": 10, "session_id": "s", "resume_gateway_url": "wss://x", "user": user_json(id="42"), "guilds": []})
    )
    assert cache.user is not None
    assert cache.user.id == Snowflake(42)
    previous = apply(cache, EventName.USER_UPDATE, user_json(id="42", username="renamed"))
    assert previous is not None
    assert cache.user.username == "renamed"


def test_events_for_an_unknown_guild_change_nothing() -> None:
    cache = StateCache()
    assert apply(cache, EventName.CHANNEL_CREATE, channel_json()) is None
    assert apply(cache, EventName.GUILD_ROLE_CREATE, {"guild_id": "7", "role": role_json()}) is None
    assert cache.guilds == {}


def test_receive_updates_the_cache_before_binding() -> None:
    client = RecordingClient()
    client.receive(parse_dispatch(EventName.GUILD_CREATE, guild_create_json()))
    received = client.receive(
        parse_dispatch(EventName.GUILD_ROLE_UPDATE, {"guild_id": "7", "role": role_json(name="admins")})
    )
    assert isinstance(received.event, Role)
    assert received.event.name == "admins"
    assert received.previous is not None
    state = client.cache.guild(GUILD)
    assert state is not None
    assert state.roles[Snowflake(8)].name == "admins"


def test_receive_binds_events_the_cache_ignores() -> None:
    client = RecordingClient()
    received = client.receive(parse_dispatch(EventName.CHANNEL_CREATE, channel_json()))
    assert isinstance(received.event, Channel)
    assert received.previous is None


def test_member_remove_carries_the_membership_the_cache_knew() -> None:
    client = RecordingClient()
    client.receive(parse_dispatch(EventName.GUILD_CREATE, guild_create_json()))
    received = client.receive(parse_dispatch(EventName.GUILD_MEMBER_REMOVE, {"guild_id": "7", "user": user_json()}))
    assert isinstance(received.event, MemberRemove)
    member = received.event.member
    assert member is not None
    assert [role.id for role in member.roles] == [Snowflake(8)]
    assert member.guild_id == GUILD


def test_member_remove_of_an_unknown_member_has_no_membership() -> None:
    client = RecordingClient()
    received = client.receive(parse_dispatch(EventName.GUILD_MEMBER_REMOVE, {"guild_id": "7", "user": user_json()}))
    assert isinstance(received.event, MemberRemove)
    assert received.event.member is None
