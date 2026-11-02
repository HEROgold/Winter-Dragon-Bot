"""Unit tests: lasting teams, their captain rules, the split helpers and the /team cog (no network)."""

from datetime import UTC, datetime, timedelta
from random import Random
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_bot.commands import Lookup
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive
from wd_discord.gateway.events import InteractionDataOption
from wd_errors import Refused

from winter_dragon.cogs.team import service
from winter_dragon.cogs.team.cog import Teams
from winter_dragon.cogs.team.models import Team, TeamKind, TeamMember, TeamOrigin
from winter_dragon.cogs.team.split import split_into, split_into_teams


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine
    from wd_discord.testing import RecordingClient


GUILD_ID = 1
INVOKER = 3
"""The default invoking user of the interaction fixtures."""
BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _seed(engine: Engine, captain: int, *others: tuple[int, int], name: str = "Crew") -> int:
    """Store a lasting team with ``captain`` and the ``(user_id, minutes_after_base)`` members; return its ID."""
    with Session(engine) as session:
        team = Team(name=name, kind=TeamKind.LASTING, origin=TeamOrigin.CREATED, captain_id=captain)
        session.add(team)
        session.flush()
        session.add(TeamMember(team_id=team.id or 0, user_id=captain, joined_at=BASE))
        for user_id, minutes in others:
            session.add(TeamMember(team_id=team.id or 0, user_id=user_id, joined_at=BASE + timedelta(minutes=minutes)))
        session.commit()
        return team.id or 0


def _member_ids(engine: Engine, team_id: int) -> list[int]:
    with Session(engine) as session:
        return [member.user_id for member in service.members_of(session, team_id)]


def _captain(engine: Engine, team_id: int) -> int | None:
    with Session(engine) as session:
        return session.get_one(Team, team_id).captain_id


# --- The service -----------------------------------------------------------------------------------------------------


def test_create_makes_a_lasting_team_with_the_captain_as_only_member(engine: Engine) -> None:
    with Session(engine) as session:
        team = service.create_team(session, "  Crew  ", captain_id=INVOKER)
        session.commit()
        team_id = team.id or 0
    with Session(engine) as session:
        stored = session.get_one(Team, team_id)
        assert stored.name == "Crew"
        assert stored.kind is TeamKind.LASTING
        assert stored.origin is TeamOrigin.CREATED
        assert stored.captain_id == INVOKER
        assert stored.ended_at is None
    assert _member_ids(engine, team_id) == [INVOKER]


def test_create_refuses_an_empty_name(engine: Engine) -> None:
    with Session(engine) as session, pytest.raises(Refused, match="A team needs a name."):
        service.create_team(session, "   ", captain_id=INVOKER)


def test_a_non_captain_leaving_keeps_the_captain(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session:
        service.leave(session, session.get_one(Team, team_id), 4)
        session.commit()
    assert _captain(engine, team_id) == INVOKER
    assert _member_ids(engine, team_id) == [INVOKER]


def test_captain_leaving_hands_over_to_the_longest_standing_member(engine: Engine) -> None:
    # Member 4 is stored before member 5 but joined later, so the handover must follow joined_at, not the row order.
    team_id = _seed(engine, INVOKER, (4, 2), (5, 1))
    with Session(engine) as session:
        service.leave(session, session.get_one(Team, team_id), INVOKER)
        session.commit()
    assert _captain(engine, team_id) == 5
    assert _member_ids(engine, team_id) == [5, 4]


def test_the_last_member_leaving_soft_deletes_the_team(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER)
    with Session(engine) as session:
        service.leave(session, session.get_one(Team, team_id), INVOKER)
        session.commit()
    with Session(engine) as session:
        assert session.exec(alive(Team)).all() == []
        assert session.get_one(Team, team_id).deleted_at is not None


def test_a_non_member_leaving_is_refused(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session, pytest.raises(Refused, match="You aren't in that team."):
        service.leave(session, session.get_one(Team, team_id), 9)


# --- The split helpers -----------------------------------------------------------------------------------------------


def test_split_into_keeps_every_id_and_sizes_differ_by_at_most_one() -> None:
    teams = split_into(list(range(7)), 3, Random(0))
    assert sorted(len(team) for team in teams) == [2, 2, 3]
    assert sorted(user_id for team in teams for user_id in team) == list(range(7))


def test_split_into_returns_nothing_for_too_few_players_or_no_teams() -> None:
    assert split_into([1, 2], 3, Random(0)) == []
    assert split_into([1, 2, 3], 0, Random(0)) == []


def test_split_into_teams_still_refuses_fewer_than_two_players() -> None:
    assert split_into_teams([1, 2, 3], 2, Random(0)) == []


# --- The cog ---------------------------------------------------------------------------------------------------------


def _cog(engine: Engine, client: RecordingClient) -> Teams:
    return detached_cog(Teams, engine=engine, client=client)


def _response(discord_client: RecordingClient) -> dict[str, object]:
    return discord_client.interaction_responses()[-1]["data"]


async def test_create_stores_the_team_and_replies(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    options = [InteractionDataOption(name="name", type=3, value="Crew")]
    await Teams.create.invoke(
        _cog(engine, discord_client),
        make_interaction("team", options=options, guild_id=GUILD_ID, channel_id=20),
        options,
    )

    (embed,) = _response(discord_client)["embeds"]
    assert embed["description"] == "Created **Crew**; you're its captain."
    with Session(engine) as session:
        team = session.exec(alive(Team)).one()
        assert team.name == "Crew"
        assert team.captain_id == INVOKER
    assert _member_ids(engine, team.id or 0) == [INVOKER]


async def test_show_lists_the_captain_and_members(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    options = [_team_option(engine, team_id)]
    await Teams.show.invoke(
        _cog(engine, discord_client),
        make_interaction("team", options=options, guild_id=GUILD_ID, channel_id=20),
        options,
    )

    embed = _response(discord_client)["embeds"][0]
    assert embed["title"] == "Crew"
    fields = {field["name"]: field["value"] for field in embed["fields"]}
    assert fields == {"Captain": f"<@{INVOKER}>", "Members (2)": f"<@{INVOKER}>, <@4>"}


async def test_leave_removes_the_invoker_and_hands_over_the_captaincy(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    options = [_team_option(engine, team_id)]
    await Teams.leave_team.invoke(
        _cog(engine, discord_client),
        make_interaction("team", options=options, guild_id=GUILD_ID, channel_id=20),
        options,
    )

    assert _response(discord_client)["embeds"][0]["description"] == "You left **Crew**."
    assert _member_ids(engine, team_id) == [4]
    assert _captain(engine, team_id) == 4


async def test_team_choices_suggests_only_the_invokers_teams(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    mine = _seed(engine, INVOKER, name="Mine")
    _seed(engine, 4, name="Theirs")
    cog = _cog(engine, discord_client)

    choices = await cog.team_choices(make_interaction("team", options=[], guild_id=GUILD_ID, channel_id=20), "")

    assert [choice.name for choice in choices] == ["Mine"]
    assert choices[0].value == Lookup.choice(_team_row(engine, mine), "Mine").value


def _team_row(engine: Engine, team_id: int) -> Team:
    with Session(engine) as session:
        return session.get_one(Team, team_id)


def _team_option(engine: Engine, team_id: int) -> InteractionDataOption:
    """The ``team`` option as the autocomplete suggested it for the team."""
    team = _team_row(engine, team_id)
    return InteractionDataOption(name="team", type=3, value=Lookup.choice(team, team.name).value)
