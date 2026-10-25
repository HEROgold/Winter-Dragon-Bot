"""Unit tests: guild entities answer from the client's cache, and their fetches fill it."""

from wd_discord import Guild, Member, Role
from wd_discord.gateway import EventName, parse_dispatch
from wd_discord.snowflake import Snowflake
from wd_discord.testing import GUILD_JSON, RecordingClient, channel_json, guild_create_json, member_json, role_json


def connected(**changes: object) -> RecordingClient:
    """Return a client that received GUILD_CREATE for guild 7."""
    client = RecordingClient()
    client.receive(parse_dispatch(EventName.GUILD_CREATE, guild_create_json(**changes)))
    return client


def test_a_partial_guild_answers_from_the_cache() -> None:
    client = connected()
    guild = client.guilds.partial(7)
    cached = guild.cached
    assert isinstance(cached, Guild)
    assert cached.name == "My Guild"
    assert [role.name for role in guild.roles or []] == ["mods"]
    assert [channel.id for channel in guild.channels or []] == [Snowflake(5)]
    assert [member.id for member in guild.members or []] == [Snowflake(3)]
    assert [voice.channel for voice in guild.voice_states or []] == [guild.channel(5)]
    assert client.sent == []


def test_get_finds_one_cached_thing() -> None:
    client = connected()
    guild = client.guilds.partial(7)
    assert isinstance(guild.get_role(8), Role)
    assert isinstance(guild.get_member(3), Member)
    channel = guild.get_channel(5)
    assert channel is not None
    assert channel.guild == guild
    assert guild.get_voice_state(guild.member(3)) is not None
    assert guild.get_role(404) is None


def test_an_unknown_guild_knows_nothing() -> None:
    guild = RecordingClient().guilds.partial(7)
    assert guild.cached is None
    assert guild.roles is None
    assert guild.channels is None
    assert guild.members is None
    assert guild.get_member(3) is None


def test_a_large_guild_has_no_complete_member_list_but_finds_members_it_saw() -> None:
    guild = connected(large=True).guilds.partial(7)
    assert guild.members is None
    assert guild.get_member(3) is not None


def test_cached_reads_follow_later_events() -> None:
    client = connected()
    client.receive(parse_dispatch(EventName.GUILD_ROLE_UPDATE, {"guild_id": "7", "role": role_json(name="admins")}))
    role = client.guilds.partial(7).get_role(8)
    assert role is not None
    assert role.name == "admins"


def test_a_guild_entity_prefers_the_cache_over_its_own_snapshot() -> None:
    client = connected()
    snapshot = client.guilds.partial(7).cached
    assert snapshot is not None
    client.receive(parse_dispatch(EventName.GUILD_ROLE_DELETE, {"guild_id": "7", "role_id": "8"}))
    assert list(snapshot.roles) == []


def test_a_fetched_guild_outside_the_cache_reads_its_own_data() -> None:
    client = RecordingClient()
    guild = Guild(client, parse_dispatch(EventName.GUILD_UPDATE, {**GUILD_JSON, "roles": [role_json()]}))
    assert [role.name for role in guild.roles] == ["mods"]


async def test_fetching_the_guild_fills_the_cache() -> None:
    client = RecordingClient()
    client.reply("GET", "/guilds/1", {**GUILD_JSON, "roles": [role_json()]})
    guild = client.guilds.partial(1)
    assert guild.cached is None
    await guild.fetch()
    assert guild.cached is not None
    assert guild.get_role(8) is not None
    assert guild.channels is None  # a fetched guild comes without its channels


async def test_fetching_channels_and_members_fills_a_known_guild() -> None:
    client = RecordingClient()
    client.reply("GET", "/guilds/1", GUILD_JSON)
    client.reply("GET", "/guilds/1/channels", [channel_json(guild_id="1")])
    client.reply("GET", "/guilds/1/members", [member_json()])
    guild = client.guilds.partial(1)
    await guild.fetch()
    await guild.fetch_channels()
    await guild.fetch_members()
    assert [channel.id for channel in guild.channels or []] == [Snowflake(5)]
    assert guild.get_channel(5) is not None
    assert guild.get_member(3) is not None
    assert guild.members is None  # one page doesn't make the member list complete


async def test_fetching_roles_replaces_the_cached_roles() -> None:
    client = connected()
    client.reply("GET", "/guilds/7/roles", [role_json(id="9", name="new")])
    guild = client.guilds.partial(7)
    await guild.fetch_roles()
    assert [role.name for role in guild.roles or []] == ["new"]


def test_a_member_s_roles_are_full_when_the_cache_knows_them() -> None:
    from wd_discord import PartialRole

    client = connected(members=[member_json(roles=["8", "404"])])
    member = client.guilds.partial(7).get_member(3)
    assert member is not None
    known, unknown = member.roles
    assert isinstance(known, Role)
    assert known.name == "mods"
    assert unknown == PartialRole(client, Snowflake(404), Snowflake(7))


def test_the_cached_guild_carries_its_current_roles() -> None:
    client = connected()
    client.receive(parse_dispatch(EventName.GUILD_ROLE_DELETE, {"guild_id": "7", "role_id": "8"}))
    client.receive(parse_dispatch(EventName.GUILD_ROLE_CREATE, {"guild_id": "7", "role": role_json(id="9")}))
    cached = client.guilds.partial(7).cached
    assert cached is not None
    assert [role.id for role in cached.model.roles] == [Snowflake(9)]
