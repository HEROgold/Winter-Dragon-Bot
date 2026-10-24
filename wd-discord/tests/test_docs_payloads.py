"""Property tests: any payload shaped as the Discord docs describe parses, keeps every field, and dumps back unchanged."""

from typing import Any

from hypothesis import given, settings
from wd_discord.cache import StateCache
from wd_discord.gateway import EventName, parse_dispatch
from wd_discord.resources.channel import Channel
from wd_discord.resources.guild import GuildMember, Role
from wd_discord.resources.user import User
from wd_discord.resources.voice import VoiceState
from wd_discord.snowflake import Snowflake
from wd_discord.testing import GUILD_JSON
from wd_discord.testing.strategies import channels, guild_creates, members, roles, users, voice_states


@given(users())
def test_a_user_parses_and_round_trips(data: dict[str, Any]) -> None:
    user = User.model_validate(data)
    assert user.model_extra == {}
    assert str(user.id) == data["id"]
    assert user.username == data["username"]
    assert User.model_validate(user.model_dump(mode="json")) == user


@given(roles())
def test_a_role_parses_and_round_trips(data: dict[str, Any]) -> None:
    role = Role.model_validate(data)
    assert role.model_extra == {}
    assert int(role.permissions) == int(data["permissions"])
    assert role.color == data["color"]
    assert Role.model_validate(role.model_dump(mode="json")) == role


@given(members())
def test_a_member_parses_and_round_trips(data: dict[str, Any]) -> None:
    member = GuildMember.model_validate(data)
    assert member.model_extra == {}
    assert [str(role) for role in member.roles] == data["roles"]
    assert GuildMember.model_validate(member.model_dump(mode="json")) == member


@given(channels())
def test_a_channel_parses_and_round_trips(data: dict[str, Any]) -> None:
    channel = Channel.model_validate(data)
    assert channel.model_extra == {}
    assert channel.type == data["type"]
    assert Channel.model_validate(channel.model_dump(mode="json")) == channel


@given(voice_states())
def test_a_voice_state_parses_and_round_trips(data: dict[str, Any]) -> None:
    state = VoiceState.model_validate(data)
    assert state.model_extra == {}
    assert (str(state.channel_id) if state.channel_id else None) == data["channel_id"]
    assert VoiceState.model_validate(state.model_dump(mode="json")) == state


@settings(deadline=None)  # parses a whole guild per example; slow CI runners overrun the default
@given(guild_creates(guild={**GUILD_JSON, "id": "7"}))
def test_guild_create_puts_every_role_channel_member_and_voice_state_in_the_cache(data: dict[str, Any]) -> None:
    cache = StateCache()
    cache.apply(parse_dispatch(EventName.GUILD_CREATE, data))

    state = cache.guild(Snowflake(7))
    assert state is not None
    assert state.channels is not None
    assert state.voice_states is not None
    assert {str(role) for role in state.roles} == {role["id"] for role in data["roles"]}
    assert {str(channel) for channel in state.channels} == {channel["id"] for channel in data["channels"]}
    assert all(channel.guild_id == Snowflake(7) for channel in state.channels.values())
    assert {str(member) for member in state.members} == {member["user"]["id"] for member in data["members"]}
    assert {str(user) for user in state.voice_states} == {voice["user_id"] for voice in data["voice_states"]}
