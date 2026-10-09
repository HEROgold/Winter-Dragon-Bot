"""Unit tests: the /stats commands, the stats channels' names and their periodic update (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, select
from wd_bot.checks import is_owner, member_has
from wd_bot.registry import CommandRegistry
from wd_discord.permissions import Permissions
from wd_discord.testing import GUILD_JSON, RecordingClient

from winter_dragon.cogs.stats import GuildCounts, PeakOnline, StatChannel, StatKind, Stats, channel_name, stats_embed


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine


GUILD_ID = 1
COUNTED_GUILD = {**GUILD_JSON, "approximate_member_count": 10, "approximate_presence_count": 6, "afk_channel_id": "30"}
MEMBERS = [
    {
        "user": {"id": str(user_id), "username": f"u{user_id}", "discriminator": "0", "bot": user_id > 7},
        "roles": [],
        "joined_at": None,
        "deaf": False,
        "mute": False,
    }  # noqa: E501
    for user_id in range(3, 10)
]
"""Seven members, two of them (8 and 9) bots."""
APPLICATION = {
    "id": "2",
    "name": "bot",
    "icon": None,
    "description": "",
    "bot_public": True,
    "bot_require_code_grant": False,
    "verify_key": "k",
    "team": None,
    "owner": {"id": "3", "username": "asker", "discriminator": "0"},
}  # noqa: E501
COUNTS = GuildCounts(members=10, bots=2, online=6, created=datetime(2015, 1, 1, tzinfo=UTC))


def _guild_api(client: RecordingClient) -> None:
    client.reply("GET", f"/guilds/{GUILD_ID}", COUNTED_GUILD)
    client.reply("GET", f"/guilds/{GUILD_ID}/members", MEMBERS)


def _cog(engine: Engine, client: RecordingClient) -> Stats:
    cog = Stats.__new__(Stats)
    cog.bot = SimpleNamespace(client=client, registry=CommandRegistry())  # pyright: ignore[reportAttributeAccessIssue]
    cog.session = Session(engine)
    return cog


def _reply(client: RecordingClient) -> str:
    return client.requests_to("POST", "/webhooks/2/tok")[-1].json["content"]


def test_counts_leave_bots_out_of_users() -> None:
    assert (COUNTS.users, COUNTS.online_users) == (8, 4)
    assert channel_name(StatKind.USERS, COUNTS, 5) == "Total Users: 8"
    assert channel_name(StatKind.ONLINE, COUNTS, 5) == "Online Users: 4"
    assert channel_name(StatKind.BOTS, COUNTS, 5) == "Total Bots: 2"
    assert channel_name(StatKind.CREATED, COUNTS, 5) == "Created On: 2015-01-01"
    assert channel_name(StatKind.PEAK, COUNTS, 5) == "Peak Online: 5"


def test_embed_shows_no_afk_channel_without_failing() -> None:
    fields = {field.name: field.value for field in stats_embed("Guild", COUNTS, None).fields or []}
    assert fields["AFK channel"] == "None"
    assert fields["Users"] == "8"


async def test_show_counts_members_bots_and_online(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    _guild_api(discord_client)
    await Stats.show.invoke(_cog(engine, discord_client), make_interaction("stats", guild_id=GUILD_ID), [])

    (embed,) = discord_client.interaction_responses()[0]["data"]["embeds"]
    fields = {field["name"]: field["value"] for field in embed["fields"]}
    assert (fields["Users"], fields["Bots"], fields["Online"], fields["AFK channel"]) == ("8", "2", "4", "<#30>")


async def test_add_needs_manage_channels(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    interaction = make_interaction("stats", guild_id=GUILD_ID, permissions=Permissions.SEND_MESSAGES)
    await Stats.add.invoke(_cog(engine, discord_client), interaction, [])

    assert discord_client.interaction_responses()[0]["data"]["content"] == "You need the Manage Channels permission for that."


async def test_add_creates_a_locked_category_of_named_channels(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    _guild_api(discord_client)
    created = [{"id": str(40 + index), "type": 2 if index else 4, "guild_id": "1"} for index in range(6)]
    discord_client.reply_each("POST", f"/guilds/{GUILD_ID}/channels", *created)
    interaction = make_interaction("stats", guild_id=GUILD_ID, permissions=Permissions.MANAGE_CHANNELS)

    await Stats.add.invoke(_cog(engine, discord_client), interaction, [])

    posts = discord_client.requests_to("POST", f"/guilds/{GUILD_ID}/channels")
    category = posts[0].json
    assert category["type"] == 4
    assert category["permission_overwrites"] == [
        {"id": "1", "type": 0, "allow": str(int(Permissions.VIEW_CHANNEL)), "deny": str(int(Permissions.CONNECT))},
    ]
    assert [post.json["name"] for post in posts[1:]] == [
        "Total Users: 8",
        "Online Users: 4",
        "Total Bots: 2",
        "Created On: 2015-01-01",
        "Peak Online: 4",
    ]
    assert all(post.json["parent_id"] == "40" for post in posts[1:])
    with Session(engine) as session:
        assert len(session.exec(select(StatChannel)).all()) == 6
        assert session.exec(select(PeakOnline)).one().peak == 4
    assert _reply(discord_client) == "Stats channels are set up."


async def test_update_renames_only_changed_channels_and_forgets_deleted_ones(engine: Engine) -> None:
    client = RecordingClient()
    _guild_api(client)
    client.reply(
        "GET",
        f"/guilds/{GUILD_ID}/channels",
        [{"id": "41", "type": 2, "name": "Total Users: 8"}, {"id": "42", "type": 2, "name": "Online Users: 1"}],
    )
    client.reply("PATCH", "/channels/42", {"id": "42", "type": 2, "name": "Online Users: 4"})
    with Session(engine) as session:
        session.add_all(
            [
                StatChannel(guild_id=GUILD_ID, channel_id=41, kind=StatKind.USERS),
                StatChannel(guild_id=GUILD_ID, channel_id=42, kind=StatKind.ONLINE),
                StatChannel(guild_id=GUILD_ID, channel_id=43, kind=StatKind.BOTS),
                PeakOnline(guild_id=GUILD_ID, peak=9),
            ],
        )
        session.commit()

    await _cog(engine, client).update_guild(GUILD_ID)

    (rename,) = [sent for sent in client.sent if sent.method == "PATCH"]
    assert (rename.path, rename.json) == ("/channels/42", {"name": "Online Users: 4"})
    with Session(engine) as session:
        assert {stat.channel_id for stat in session.exec(select(StatChannel))} == {41, 42}
        assert session.exec(select(PeakOnline)).one().peak == 9


async def test_reset_is_for_bot_owners_only(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply(
        "GET", "/applications/@me", {**APPLICATION, "owner": {"id": "99", "username": "o", "discriminator": "0"}}
    )
    await Stats.reset.invoke(_cog(engine, discord_client), make_interaction("stats", guild_id=GUILD_ID), [])

    assert discord_client.interaction_responses()[0]["data"]["content"] == "Only the bot's owners can do that."


@pytest.mark.parametrize(("user_id", "expected"), [(3, True), (4, False)])
async def test_is_owner_reads_the_application(user_id: int, *, expected: bool) -> None:
    client = RecordingClient()
    client.reply("GET", "/applications/@me", APPLICATION)
    assert await is_owner(client, user_id) is expected


def test_member_has_counts_administrators(make_interaction: InteractionFactory) -> None:
    assert member_has(make_interaction(permissions=Permissions.ADMINISTRATOR), Permissions.MANAGE_CHANNELS)
    assert not member_has(make_interaction(), Permissions.MANAGE_CHANNELS)
