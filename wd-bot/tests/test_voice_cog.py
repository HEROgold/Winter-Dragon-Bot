"""Unit tests: /voice split posts teams in a voice channel, Move gives each team a channel, and empty ones end (no network)."""

import asyncio
from random import Random
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive
from wd_discord import VoiceState, bind
from wd_discord.gateway import EventName, parse_dispatch
from wd_discord.gateway.events import InteractionDataOption
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake
from wd_discord.testing import RecordingClient, member_json, message_json, user_json, voice_state_json

from winter_dragon.cogs.team import service
from winter_dragon.cogs.team.models import Team, TeamKind, TeamOrigin
from winter_dragon.cogs.voice import TeamVoiceChannel, Voice
from winter_dragon.voice_channels import VoiceOccupancy


if TYPE_CHECKING:
    from conftest import ComponentInteractionFactory, InteractionFactory
    from sqlalchemy import Engine


GUILD_ID = 1
VC = 70
"""The voice channel the members sit in, and the chat the split posts in."""
CATEGORY_ID = 49
NEW_CHANNEL_ID = 60
MEMBERS = (3, 4, 5)
OUTSIDER = 9
NEW_CHANNEL = {"id": str(NEW_CHANNEL_ID), "type": 2, "guild_id": str(GUILD_ID), "name": "Team 1", "parent_id": str(CATEGORY_ID)}


def _member(user_id: int) -> User:
    return User.model_validate({"id": str(user_id), "username": f"user{user_id}", "discriminator": "0"})


def _member_json(user_id: int) -> dict[str, object]:
    return member_json(user=user_json(id=str(user_id), username=f"user{user_id}"), nick=None)


def _state(client: RecordingClient, channel_id: int | None, user_id: int) -> VoiceState:
    data = voice_state_json(
        guild_id=str(GUILD_ID),
        channel_id=None if channel_id is None else str(channel_id),
        user_id=str(user_id),
        member=_member_json(user_id),
    )
    state = bind(client, parse_dispatch(EventName.VOICE_STATE_UPDATE, data))
    assert isinstance(state, VoiceState)
    return state


def _cog(engine: Engine, client: RecordingClient) -> Voice:
    cog = detached_cog(Voice, engine=engine, client=client)
    cog.voice = VoiceOccupancy()
    cog._lock = asyncio.Lock()  # noqa: SLF001 - what __init__ sets up
    cog.rng = Random(0)
    return cog


def _occupy(cog: Voice, *user_ids: int) -> None:
    for user_id in user_ids:
        cog.voice.move(Snowflake(GUILD_ID), Snowflake(user_id), Snowflake(VC))


def _split_options(teams: int = 2, move: bool | None = None) -> list[InteractionDataOption]:
    options = [InteractionDataOption(name="teams", type=4, value=teams)]
    if move is not None:
        options.append(InteractionDataOption(name="move", type=5, value=move))
    return options


async def _split(
    cog: Voice,
    make_interaction: InteractionFactory,
    options: list[InteractionDataOption],
) -> None:
    await Voice.split.invoke(
        cog, make_interaction("voice", options=options, guild_id=GUILD_ID, channel_id=VC, user=_member(3)), options
    )


def _content(client: RecordingClient) -> str:
    return client.interaction_responses()[-1]["data"]["content"]


def _buttons(client: RecordingClient) -> list[dict[str, object]]:
    (post,) = client.requests_to("POST", f"/channels/{VC}/messages")
    return [button for row in post.json["components"] for button in row["components"]]


def _teams_by_members(engine: Engine) -> dict[int, list[int]]:
    """Return each alive team's ID mapped to its member IDs."""
    with Session(engine) as session:
        return {
            team.id or 0: [member.user_id for member in service.members_of(session, team)] for team in session.exec(alive(Team))
        }


def _team_with(engine: Engine, user_id: int, size: int | None = None) -> int:
    """Return the ID of a split team holding ``user_id``, with ``size`` members when given."""
    for team_id, members in _teams_by_members(engine).items():
        if user_id in members and (size is None or len(members) == size):
            return team_id
    msg = f"no team holds {user_id} with size {size}"
    raise AssertionError(msg)


async def _press(cog: Voice, make_component_interaction: ComponentInteractionFactory, team_id: int, user_id: int) -> None:
    await Voice.move_button.invoke(
        cog,
        make_component_interaction(f"team-move:{team_id}:{VC}", guild_id=GUILD_ID, user=_member(user_id)),
        [str(team_id), str(VC)],
    )


def _team_channels(engine: Engine) -> list[tuple[int, int]]:
    with Session(engine) as session:
        return [(row.id, row.team_id) for row in session.exec(alive(TeamVoiceChannel))]


@pytest.fixture
def client(discord_client: RecordingClient) -> RecordingClient:
    discord_client.reply(
        "GET", f"/channels/{VC}", {"id": str(VC), "type": 2, "guild_id": str(GUILD_ID), "parent_id": str(CATEGORY_ID)}
    )
    discord_client.reply("POST", f"/guilds/{GUILD_ID}/channels", NEW_CHANNEL)
    for user_id in (*MEMBERS, OUTSIDER):
        discord_client.reply("PATCH", f"/guilds/{GUILD_ID}/members/{user_id}", _member_json(user_id))
    discord_client.reply("POST", f"/channels/{VC}/messages", message_json(channel_id=str(VC)))
    discord_client.reply("DELETE", f"/channels/{NEW_CHANNEL_ID}", NEW_CHANNEL)
    return discord_client


async def test_split_refuses_a_caller_who_is_not_in_voice(
    engine: Engine,
    make_interaction: InteractionFactory,
    client: RecordingClient,
) -> None:
    await _split(_cog(engine, client), make_interaction, _split_options())

    assert _content(client) == "Join a voice channel first."
    assert client.requests_to("POST", f"/channels/{VC}/messages") == []


async def test_split_refuses_too_few_people_for_the_teams(
    engine: Engine,
    make_interaction: InteractionFactory,
    client: RecordingClient,
) -> None:
    cog = _cog(engine, client)
    _occupy(cog, 3)

    await _split(cog, make_interaction, _split_options(teams=2))

    assert _content(client) == "There aren't enough people in your voice channel for 2 teams."
    with Session(engine) as session:
        assert session.exec(alive(Team)).all() == []


async def test_split_stores_voice_split_teams_and_posts_move_and_keep_buttons(
    engine: Engine,
    make_interaction: InteractionFactory,
    client: RecordingClient,
) -> None:
    cog = _cog(engine, client)
    _occupy(cog, *MEMBERS)

    await _split(cog, make_interaction, _split_options(teams=2, move=True))

    with Session(engine) as session:
        teams = list(session.exec(alive(Team)))
        assert sorted(team.name for team in teams) == ["Team 1", "Team 2"]
        assert {(team.kind, team.origin) for team in teams} == {(TeamKind.TEMPORARY, TeamOrigin.VOICE_SPLIT)}
    assert sorted(user for members in _teams_by_members(engine).values() for user in members) == list(MEMBERS)
    labels = [button["label"] for button in _buttons(client)]
    assert labels == ["Move to Team 1", "Keep Team 1", "Move to Team 2", "Keep Team 2"]
    assert _content(client) == f"Posted the teams in <#{VC}>."


async def test_split_without_move_posts_keep_buttons_only(
    engine: Engine,
    make_interaction: InteractionFactory,
    client: RecordingClient,
) -> None:
    cog = _cog(engine, client)
    _occupy(cog, *MEMBERS)

    await _split(cog, make_interaction, _split_options(teams=2, move=False))

    assert [button["label"] for button in _buttons(client)] == ["Keep Team 1", "Keep Team 2"]


async def test_the_first_move_press_creates_the_team_channel_and_moves_the_presser(
    engine: Engine,
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    client: RecordingClient,
) -> None:
    cog = _cog(engine, client)
    _occupy(cog, *MEMBERS)
    await _split(cog, make_interaction, _split_options(teams=2, move=True))
    team_id = _team_with(engine, 3)

    await _press(cog, make_component_interaction, team_id, 3)

    (create,) = client.requests_to("POST", f"/guilds/{GUILD_ID}/channels")
    assert create.json["parent_id"] == str(CATEGORY_ID)
    assert create.json["type"] == 2
    (move,) = client.requests_to("PATCH", f"/guilds/{GUILD_ID}/members/3")
    assert move.json == {"channel_id": str(NEW_CHANNEL_ID)}
    assert _team_channels(engine) == [(NEW_CHANNEL_ID, team_id)]
    assert _content(client) == f"Moved you to <#{NEW_CHANNEL_ID}>."


async def test_a_failed_move_deletes_the_channel_it_just_created(
    engine: Engine,
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    client: RecordingClient,
) -> None:
    cog = _cog(engine, client)
    _occupy(cog, *MEMBERS)
    await _split(cog, make_interaction, _split_options(teams=2, move=True))
    team_id = _team_with(engine, 3)
    client.reply(
        "PATCH",
        f"/guilds/{GUILD_ID}/members/3",
        {"code": 40032, "message": "Target user is not connected to voice."},
        status=400,
    )
    client.reply("DELETE", f"/channels/{NEW_CHANNEL_ID}", {"id": str(NEW_CHANNEL_ID), "type": 2, "guild_id": str(GUILD_ID)})

    await _press(cog, make_component_interaction, team_id, 3)

    assert len(client.requests_to("DELETE", f"/channels/{NEW_CHANNEL_ID}")) == 1
    assert _team_channels(engine) == []
    assert _content(client).startswith("I couldn't move you")


async def test_a_second_press_by_a_teammate_reuses_the_channel(
    engine: Engine,
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    client: RecordingClient,
) -> None:
    cog = _cog(engine, client)
    _occupy(cog, *MEMBERS)
    await _split(cog, make_interaction, _split_options(teams=2, move=True))
    team_id = _team_with(engine, 3, size=2)
    first, second = _teams_by_members(engine)[team_id]

    await _press(cog, make_component_interaction, team_id, first)
    await _press(cog, make_component_interaction, team_id, second)

    assert len(client.requests_to("POST", f"/guilds/{GUILD_ID}/channels")) == 1
    assert client.requests_to("PATCH", f"/guilds/{GUILD_ID}/members/{second}")[0].json == {"channel_id": str(NEW_CHANNEL_ID)}
    assert _team_channels(engine) == [(NEW_CHANNEL_ID, team_id)]


async def test_a_non_member_pressing_move_is_refused(
    engine: Engine,
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    client: RecordingClient,
) -> None:
    cog = _cog(engine, client)
    _occupy(cog, *MEMBERS)
    await _split(cog, make_interaction, _split_options(teams=2, move=True))
    team_id = _team_with(engine, 3)

    await _press(cog, make_component_interaction, team_id, OUTSIDER)

    assert _content(client) == "Only this team's members can move to its channel."
    assert client.requests_to("POST", f"/guilds/{GUILD_ID}/channels") == []
    assert client.requests_to("PATCH", f"/guilds/{GUILD_ID}/members/{OUTSIDER}") == []


async def test_leaving_an_empty_team_channel_deletes_it_and_ends_the_team(
    engine: Engine,
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    client: RecordingClient,
) -> None:
    cog = _cog(engine, client)
    _occupy(cog, *MEMBERS)
    await _split(cog, make_interaction, _split_options(teams=2, move=True))
    team_id = _team_with(engine, 3)
    await _press(cog, make_component_interaction, team_id, 3)
    cog.voice.move(Snowflake(GUILD_ID), Snowflake(3), Snowflake(NEW_CHANNEL_ID))

    await cog.on_voice_state_update(_state(client, None, 3))

    assert len(client.requests_to("DELETE", f"/channels/{NEW_CHANNEL_ID}")) == 1
    assert _team_channels(engine) == []
    with Session(engine) as session:
        assert session.get_one(Team, team_id).ended_at is not None
