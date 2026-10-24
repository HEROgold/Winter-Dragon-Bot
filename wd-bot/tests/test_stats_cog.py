"""Unit tests: the /stats commands, the stats channels' names and their periodic update (no network)."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_db.extension.lifecycle import alive
from wd_db.testing import seed
from wd_bot.checks import is_owner, member_has
from wd_bot.testing import detached_cog
from wd_discord.permissions import Permissions
from wd_discord.testing import GUILD_JSON, RecordingClient, member_json, user_json

from winter_dragon.cogs.stats import (
    GuildCounts,
    PeakOnline,
    StatChannel,
    StatKind,
    Stats,
    channel_name,
    plan_renames,
    stats_embed,
)
from winter_dragon.config import Settings


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine


GUILD_ID = 1
COUNTED_GUILD = {**GUILD_JSON, "approximate_member_count": 10, "approximate_presence_count": 6, "afk_channel_id": "30"}
MEMBERS = [
    member_json(user=user_json(id=str(user_id), username=f"u{user_id}", bot=user_id > 7)) for user_id in range(3, 10)
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
    "owner": user_json(username="asker"),
}  # noqa: E501
COUNTS = GuildCounts(members=10, bots=2, online=6, created=datetime(2015, 1, 1, tzinfo=UTC))


def _guild_api(client: RecordingClient) -> None:
    client.reply("GET", f"/guilds/{GUILD_ID}", COUNTED_GUILD)
    client.reply("GET", f"/guilds/{GUILD_ID}/members", MEMBERS)


def _cog(engine: Engine, client: RecordingClient) -> Stats:
    return detached_cog(Stats, engine=engine, client=client)


def _reply(client: RecordingClient) -> str:
    return client.requests_to("POST", "/webhooks/2/tok")[-1].json["content"]


def _embed(client: RecordingClient) -> dict[str, object]:
    return client.requests_to("POST", "/webhooks/2/tok")[-1].json["embeds"][0]


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
        assert len(session.exec(alive(StatChannel)).all()) == 6
        assert session.exec(alive(PeakOnline)).one().peak == 4
    assert _embed(discord_client) == {"description": "Stats channels are set up.", "color": int(Settings.created_color)}


async def test_update_renames_only_changed_channels_and_forgets_deleted_ones(engine: Engine) -> None:
    client = RecordingClient()
    _guild_api(client)
    client.reply(
        "GET",
        f"/guilds/{GUILD_ID}/channels",
        [{"id": "41", "type": 2, "name": "Total Users: 8"}, {"id": "42", "type": 2, "name": "Online Users: 1"}],
    )
    client.reply("PATCH", "/channels/42", {"id": "42", "type": 2, "name": "Online Users: 4"})
    seed(
        engine,
        StatChannel(id=41, guild_id=GUILD_ID, kind=StatKind.USERS),
        StatChannel(id=42, guild_id=GUILD_ID, kind=StatKind.ONLINE),
        StatChannel(id=43, guild_id=GUILD_ID, kind=StatKind.BOTS),
        PeakOnline(id=GUILD_ID, peak=9),
    )

    await _cog(engine, client).update_guild(GUILD_ID)

    (rename,) = [sent for sent in client.sent if sent.method == "PATCH"]
    assert (rename.path, rename.json) == ("/channels/42", {"name": "Online Users: 4"})
    with Session(engine) as session:
        assert {stat.id for stat in session.exec(alive(StatChannel))} == {41, 42}
        assert session.exec(alive(PeakOnline)).one().peak == 9


async def test_reset_is_for_bot_owners_only(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply(
        "GET",
        "/applications/@me",
        {**APPLICATION, "owner": user_json(id="99", username="o")},
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


def test_plan_renames_only_changed_channels_and_drops_missing_ones() -> None:
    stats = [
        StatChannel(id=40, guild_id=GUILD_ID, kind=StatKind.CATEGORY),
        StatChannel(id=41, guild_id=GUILD_ID, kind=StatKind.USERS),
        StatChannel(id=42, guild_id=GUILD_ID, kind=StatKind.PEAK),
        StatChannel(id=43, guild_id=GUILD_ID, kind=StatKind.BOTS),
    ]
    names = {40: "Renamed by hand", 41: "Total Users: 8", 42: "Peak Online: 1"}

    plan = plan_renames(stats, names, COUNTS, peak=5)

    assert plan.renames == {42: "Peak Online: 5"}
    assert [stat.id for stat in plan.gone] == [43]


async def test_remove_forgets_only_channels_that_are_gone_and_keeps_their_category(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("DELETE", "/channels/41", {"code": 50001, "message": "Missing Access"}, status=403)
    discord_client.reply("DELETE", "/channels/42", {"code": 10003, "message": "Unknown Channel"}, status=404)
    discord_client.reply("DELETE", "/channels/40", {"id": "40", "type": 4})
    seed(
        engine,
        StatChannel(id=40, guild_id=GUILD_ID, kind=StatKind.CATEGORY),
        StatChannel(id=41, guild_id=GUILD_ID, kind=StatKind.USERS),
        StatChannel(id=42, guild_id=GUILD_ID, kind=StatKind.BOTS),
    )
    interaction = make_interaction("stats", guild_id=GUILD_ID, permissions=Permissions.MANAGE_CHANNELS)

    await Stats.remove.invoke(_cog(engine, discord_client), interaction, [])

    with Session(engine) as session:
        assert {stat.id for stat in session.exec(alive(StatChannel))} == {40, 41}
    assert discord_client.requests_to("DELETE", "/channels/40") == []  # the category stays while a channel is left in it
    assert _reply(discord_client) == "I couldn't delete every stats channel; run it again to retry the rest."


async def test_add_remove_add_renames_only_the_newest_channels_and_keeps_the_peak(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    _guild_api(discord_client)
    seed(engine, PeakOnline(id=GUILD_ID, peak=9))
    first = [{"id": str(40 + index), "type": 2 if index else 4, "guild_id": "1"} for index in range(6)]
    second = [{"id": str(50 + index), "type": 2 if index else 4, "guild_id": "1"} for index in range(6)]
    discord_client.reply_each("POST", f"/guilds/{GUILD_ID}/channels", *first, *second)
    for channel in first:
        discord_client.reply("DELETE", f"/channels/{channel['id']}", channel)
    cog = _cog(engine, discord_client)

    for command in (Stats.add, Stats.remove, Stats.add):
        interaction = make_interaction("stats", guild_id=GUILD_ID, permissions=Permissions.MANAGE_CHANNELS)
        await command.invoke(cog, interaction, [])
    stale = [{"id": channel["id"], "type": 2, "name": "stale"} for channel in [*first, *second]]
    discord_client.reply("GET", f"/guilds/{GUILD_ID}/channels", stale)
    for channel in second:
        discord_client.reply("PATCH", f"/channels/{channel['id']}", {**channel, "name": "renamed"})
    await cog.update_guild(GUILD_ID)

    renamed = sorted(sent.path for sent in discord_client.sent if sent.method == "PATCH")
    assert renamed == [f"/channels/{channel_id}" for channel_id in range(51, 56)]
    posts = discord_client.requests_to("POST", f"/guilds/{GUILD_ID}/channels")
    assert [post.json["name"] for post in posts[6:]][-1] == "Peak Online: 9"
    with Session(engine) as session:
        assert session.exec(alive(PeakOnline)).one().peak == 9
