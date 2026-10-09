"""Unit tests: creating, editing and deleting channels, permission overwrites, and guild members (no network)."""

from __future__ import annotations

from wd_discord import AuditLogReason, Channel, ChannelType, Guild, Member, Permissions, is_network_error
from wd_discord.audit import MAX_REASON_LENGTH, REASON_HEADER
from wd_discord.errors import ApiResponseError, JsonErrorCode
from wd_discord.resources.channel import ChannelParams, GuildChannelParams, OverwriteParams, OverwriteType
from wd_discord.snowflake import Snowflake
from wd_discord.testing import GUILD_JSON, RecordingClient


VOICE_JSON = {"id": "20", "type": 2, "guild_id": "1", "name": "Lobby", "parent_id": "10", "user_limit": 0}
MEMBER_JSON = {
    "user": {"id": "3", "username": "someone", "discriminator": "0", "global_name": "Some One"},
    "nick": None,
    "roles": [],
    "joined_at": "2026-10-08T00:00:00+00:00",
    "deaf": False,
    "mute": False,
}
BOT_MEMBER_JSON = {**MEMBER_JSON, "user": {"id": "4", "username": "robot", "discriminator": "0", "bot": True}}


def test_reason_header_is_url_encoded_and_capped() -> None:
    assert AuditLogReason("Locked by <@1>").headers() == {REASON_HEADER: "Locked by %3C%401%3E"}
    assert len(AuditLogReason("x" * 600).headers()[REASON_HEADER]) == MAX_REASON_LENGTH


def test_channel_params_send_only_what_is_set() -> None:
    assert ChannelParams(user_limit=5).to_json() == {"user_limit": 5}
    overwrite = OverwriteParams(id=Snowflake(1), type=OverwriteType.ROLE, deny=Permissions.SEND_MESSAGES)
    assert overwrite.to_json() == {"id": "1", "type": 0, "allow": "0", "deny": str(int(Permissions.SEND_MESSAGES))}


async def test_guild_create_channel_posts_params_with_reason() -> None:
    client = RecordingClient()
    client.reply("POST", "/guilds/1/channels", VOICE_JSON)
    params = GuildChannelParams(name="Lobby", type=ChannelType.GUILD_VOICE, parent_id=Snowflake(10))

    channel = await client.guilds.partial(1).create_channel(params, reason="Setting up")

    assert isinstance(channel, Channel)
    assert channel.parent_id == Snowflake(10)
    sent = client.sent[0]
    assert sent.json == {"name": "Lobby", "type": 2, "parent_id": "10"}
    assert sent.headers == {REASON_HEADER: "Setting up"}


async def test_channel_edit_and_delete() -> None:
    client = RecordingClient()
    client.reply("PATCH", "/channels/20", {**VOICE_JSON, "name": "Renamed"})
    client.reply("DELETE", "/channels/20", VOICE_JSON)
    channel = client.channels.partial(20)

    edited = await channel.edit(ChannelParams(name="Renamed"))
    deleted = await channel.delete(reason="Empty")

    assert isinstance(edited, Channel)
    assert edited.name == "Renamed"
    assert isinstance(deleted, Channel)
    assert client.sent[0].json == {"name": "Renamed"}
    assert client.sent[0].headers == {}
    assert client.sent[1].headers == {REASON_HEADER: "Empty"}


async def test_channel_set_and_delete_permissions() -> None:
    client = RecordingClient()
    channel = client.channels.partial(20)
    overwrite = OverwriteParams(id=Snowflake(5), type=OverwriteType.MEMBER, deny=Permissions.SEND_MESSAGES)

    assert await channel.set_permissions(overwrite, reason="Lock") is None
    assert await channel.delete_permissions(5) is None

    assert [(sent.method, sent.path) for sent in client.sent] == [
        ("PUT", "/channels/20/permissions/5"),
        ("DELETE", "/channels/20/permissions/5"),
    ]
    assert client.sent[0].json == overwrite.to_json()


async def test_guild_fetch_with_counts_asks_for_them() -> None:
    client = RecordingClient()
    client.reply("GET", "/guilds/1", {**GUILD_JSON, "approximate_member_count": 12, "approximate_presence_count": 4})

    guild = await client.guilds.partial(1).fetch(with_counts=True)

    assert isinstance(guild, Guild)
    assert guild.model.approximate_presence_count == 4
    assert client.sent[0].params == {"with_counts": "true"}


async def test_guild_members_page() -> None:
    client = RecordingClient()
    client.reply("GET", "/guilds/1/members", [MEMBER_JSON, BOT_MEMBER_JSON])

    members = await client.guilds.partial(1).members(after=2, limit=50)

    assert not is_network_error(members)
    first, second = members
    assert isinstance(first, Member)
    assert (first.id, first.guild_id, first.bot, first.display_name) == (Snowflake(3), Snowflake(1), False, "Some One")
    assert second.bot
    assert client.sent[0].params == {"limit": "50", "after": "2"}


async def test_member_move_to_patches_the_voice_channel() -> None:
    client = RecordingClient()
    client.reply("PATCH", "/guilds/1/members/3", MEMBER_JSON)
    member = client.guilds.partial(1).member(3)

    moved = await member.move_to(20, reason="Own channel")
    await member.move_to(None)

    assert isinstance(moved, Member)
    assert member.mention == "<@3>"
    assert [sent.json for sent in client.sent] == [{"channel_id": "20"}, {"channel_id": None}]


async def test_an_unreadable_response_is_a_failure_not_an_exception() -> None:
    client = RecordingClient()  # no reply: an empty 204 where a channel was expected
    client.reply("GET", "/guilds/1/channels", [VOICE_JSON, {"id": "x"}])

    deleted = await client.channels.partial(20).delete()
    channels = await client.guilds.partial(1).channels()

    assert isinstance(deleted, ApiResponseError)
    assert (deleted.code, deleted.status) == (JsonErrorCode.GENERAL_ERROR, 204)
    assert isinstance(channels, ApiResponseError)


async def test_api_errors_keep_the_http_status_and_name_unknown_resources() -> None:
    client = RecordingClient()
    client.reply("DELETE", "/channels/20", {"code": 10003, "message": "Unknown Channel"}, status=404)

    error = await client.channels.partial(20).delete()

    assert isinstance(error, ApiResponseError)
    assert (error.code, error.status, error.unknown_resource) == (JsonErrorCode.UNKNOWN_CHANNEL, 404, True)
    assert not ApiResponseError(code=JsonErrorCode.MISSING_ACCESS, message="Missing Access").unknown_resource
