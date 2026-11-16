"""Unit tests: lasting teams, their captain rules, the split helpers and the /team cog (no network)."""

from datetime import UTC, datetime, timedelta
from random import Random
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import event
from sqlmodel import Session
from wd_bot.commands import Lookup
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive
from wd_discord.gateway.events import InteractionDataOption, ResolvedData
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake
from wd_errors import Refused
from wd_types.clock import utc_now

from winter_dragon.cogs.team import service
from winter_dragon.cogs.team.cog import Teams
from winter_dragon.cogs.team.models import Team, TeamKind, TeamMember, TeamOrigin
from winter_dragon.cogs.team.split import split_into, split_into_teams


if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import ComponentInteractionFactory, InteractionFactory, ModalSubmitFactory
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
        return [member.user_id for member in service.members_of(session, session.get_one(Team, team_id))]


def _captain(engine: Engine, team_id: int) -> int | None:
    with Session(engine) as session:
        return session.get_one(Team, team_id).captain_id


# --- The service -----------------------------------------------------------------------------------------------------


def test_create_makes_a_lasting_team_with_the_captain_as_only_member(engine: Engine) -> None:
    with Session(engine) as session:
        team = service.create_team(session, "  Crew  ", captain_id=Snowflake(INVOKER))
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
        service.create_team(session, "   ", captain_id=Snowflake(INVOKER))


def test_a_non_captain_leaving_keeps_the_captain(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session:
        service.leave(session, session.get_one(Team, team_id), Snowflake(4))
        session.commit()
    assert _captain(engine, team_id) == INVOKER
    assert _member_ids(engine, team_id) == [INVOKER]


def test_captain_leaving_hands_over_to_the_longest_standing_member(engine: Engine) -> None:
    # Member 4 is stored before member 5 but joined later, so the handover must follow joined_at, not the row order.
    team_id = _seed(engine, INVOKER, (4, 2), (5, 1))
    with Session(engine) as session:
        service.leave(session, session.get_one(Team, team_id), Snowflake(INVOKER))
        session.commit()
    assert _captain(engine, team_id) == 5
    assert _member_ids(engine, team_id) == [5, 4]


def test_the_last_member_leaving_soft_deletes_the_team(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER)
    with Session(engine) as session:
        service.leave(session, session.get_one(Team, team_id), Snowflake(INVOKER))
        session.commit()
    with Session(engine) as session:
        assert session.exec(alive(Team)).all() == []
        assert session.get_one(Team, team_id).deleted_at is not None


def test_a_non_member_leaving_is_refused(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session, pytest.raises(Refused, match="You aren't in that team."):
        service.leave(session, session.get_one(Team, team_id), Snowflake(9))


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


# --- Invites, kicks, captaincy and disbanding -------------------------------------------------------------------------


def _member(user_id: int) -> User:
    return User.model_validate({"id": str(user_id), "username": f"user{user_id}", "discriminator": "0"})


def _member_option(user_id: int) -> tuple[InteractionDataOption, ResolvedData]:
    """The ``member`` User option for ``user_id``, with the user it resolves to."""
    option = InteractionDataOption(name="member", type=6, value=str(user_id))
    return option, ResolvedData(users={str(user_id): _member(user_id)})


def test_join_adds_the_member_and_refuses_one_already_in_the_team(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER)
    with Session(engine) as session:
        service.join(session, session.get_one(Team, team_id), Snowflake(4))
        session.commit()
    assert _member_ids(engine, team_id) == [INVOKER, 4]
    with Session(engine) as session, pytest.raises(Refused, match="You're in that team already."):
        service.join(session, session.get_one(Team, team_id), Snowflake(4))


def test_only_the_captain_passes_require_captain(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session:
        team = session.get_one(Team, team_id)
        service.require_captain(team, Snowflake(INVOKER))
        with pytest.raises(Refused, match="Only the team's captain can do that."):
            service.require_captain(team, Snowflake(4))


def test_kick_takes_a_member_out_for_the_captain(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1), (5, 2))
    with Session(engine) as session:
        service.kick(session, session.get_one(Team, team_id), Snowflake(INVOKER), Snowflake(4))
        session.commit()
    assert _member_ids(engine, team_id) == [INVOKER, 5]


def test_kick_refuses_a_non_captain_a_self_kick_and_a_non_member(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session:
        team = session.get_one(Team, team_id)
        with pytest.raises(Refused, match="Only the team's captain can do that."):
            service.kick(session, team, Snowflake(4), Snowflake(INVOKER))
        with pytest.raises(Refused, match="Use leave to leave your own team."):
            service.kick(session, team, Snowflake(INVOKER), Snowflake(INVOKER))
        with pytest.raises(Refused, match="They aren't in that team."):
            service.kick(session, team, Snowflake(INVOKER), Snowflake(9))


def test_hand_over_makes_a_member_the_captain(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session:
        service.hand_over(session, session.get_one(Team, team_id), Snowflake(INVOKER), Snowflake(4))
        session.commit()
    assert _captain(engine, team_id) == 4


def test_hand_over_refuses_a_non_captain_and_a_non_member(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session:
        team = session.get_one(Team, team_id)
        with pytest.raises(Refused, match="Only the team's captain can do that."):
            service.hand_over(session, team, Snowflake(4), Snowflake(4))
        with pytest.raises(Refused, match="They aren't in that team."):
            service.hand_over(session, team, Snowflake(INVOKER), Snowflake(9))


def test_disband_soft_deletes_the_team_and_every_membership(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session:
        service.disband(session, session.get_one(Team, team_id), Snowflake(INVOKER))
        session.commit()
    with Session(engine) as session:
        assert session.get_one(Team, team_id).deleted_at is not None
        assert session.exec(alive(TeamMember)).all() == []


def test_disband_refuses_a_non_captain(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session, pytest.raises(Refused, match="Only the team's captain can do that."):
        service.disband(session, session.get_one(Team, team_id), Snowflake(4))


def test_a_hidden_captain_hands_the_captaincy_over(engine: Engine) -> None:
    team_id = _seed(engine, INVOKER, (4, 1))
    with Session(engine) as session:
        service.LeaveHiddenMember.on_member_hidden(session, Snowflake(INVOKER))
        session.commit()
    assert _captain(engine, team_id) == 4
    assert _member_ids(engine, team_id) == [4]


async def test_invite_replies_with_a_join_button_only_the_invitee_can_press(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    team_id = _seed(engine, INVOKER)
    member, resolved = _member_option(4)
    options = [_team_option(engine, team_id), member]
    await Teams.invite.invoke(
        _cog(engine, discord_client),
        make_interaction("team", options=options, resolved=resolved, guild_id=GUILD_ID, channel_id=20),
        options,
    )

    data = _response(discord_client)
    assert data["embeds"][0]["description"] == f"<@4>, <@{INVOKER}> invites you to **Crew**."
    (button,) = data["components"][0]["components"]
    assert button["custom_id"] == f"team-invite:{team_id}:4"
    assert button["label"] == "Join"


async def test_a_click_on_the_invite_joins_only_the_invitee(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    team_id = _seed(engine, INVOKER)
    cog = _cog(engine, discord_client)

    await Teams.accept_invite.invoke(
        cog,
        make_component_interaction(f"team-invite:{team_id}:4", guild_id=GUILD_ID, user=_member(9)),
        [str(team_id), "4"],
    )
    assert _response(discord_client)["content"] == "This invite isn't for you."
    assert _member_ids(engine, team_id) == [INVOKER]

    await Teams.accept_invite.invoke(
        cog,
        make_component_interaction(f"team-invite:{team_id}:4", guild_id=GUILD_ID, user=_member(4)),
        [str(team_id), "4"],
    )
    update = discord_client.interaction_responses()[-1]
    assert update["type"] == 7
    assert update["data"]["embeds"][0]["description"] == "<@4> joined **Crew**."
    assert _member_ids(engine, team_id) == [INVOKER, 4]


async def test_a_non_captain_cannot_kick(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    team_id = _seed(engine, 4, (INVOKER, 1), (5, 2))
    member, resolved = _member_option(5)
    options = [_team_option(engine, team_id), member]
    await Teams.kick_member.invoke(
        _cog(engine, discord_client),
        make_interaction("team", options=options, resolved=resolved, guild_id=GUILD_ID, channel_id=20),
        options,
    )

    assert _response(discord_client)["content"] == "Only the team's captain can do that."
    assert _member_ids(engine, team_id) == [4, INVOKER, 5]


# --- Temporary teams -------------------------------------------------------------------------------------------------


def _split_teams(engine: Engine, groups: list[list[int]], origin: TeamOrigin = TeamOrigin.TEXT_SPLIT) -> list[int]:
    """Store one temporary team per group through the service; return their IDs."""
    with Session(engine) as session:
        teams = service.create_temporary_teams(session, [[Snowflake(user_id) for user_id in group] for group in groups], origin)
        session.commit()
        return [team.id or 0 for team in teams]


def _temporary_row(
    engine: Engine,
    *,
    created_at: datetime,
    kind: TeamKind = TeamKind.TEMPORARY,
    origin: TeamOrigin = TeamOrigin.TEXT_SPLIT,
) -> int:
    """Store a team created at ``created_at`` directly, so its age is under the test's control; return its ID."""
    with Session(engine) as session:
        team = Team(name="Temp", kind=kind, origin=origin, created_at=created_at)
        session.add(team)
        session.commit()
        return team.id or 0


def test_create_temporary_teams_stores_numbered_unended_teams_with_their_members(engine: Engine) -> None:
    team_ids = _split_teams(engine, [[3, 4], [5, 6]])
    with Session(engine) as session:
        teams = [session.get_one(Team, team_id) for team_id in team_ids]
        assert [team.name for team in teams] == ["Team 1", "Team 2"]
        assert all(team.kind is TeamKind.TEMPORARY for team in teams)
        assert all(team.origin is TeamOrigin.TEXT_SPLIT for team in teams)
        assert all(team.captain_id is None and team.ended_at is None for team in teams)
    assert _member_ids(engine, team_ids[0]) == [3, 4]
    assert _member_ids(engine, team_ids[1]) == [5, 6]


def test_keep_makes_the_team_lasting_with_the_presser_as_captain(engine: Engine) -> None:
    (team_id,) = _split_teams(engine, [[3, 4, 5]])
    with Session(engine) as session:
        service.keep(session, session.get_one(Team, team_id), Snowflake(4), "  Owls  ")
        session.commit()
    with Session(engine) as session:
        team = session.get_one(Team, team_id)
        assert team.name == "Owls"
        assert team.kind is TeamKind.LASTING
        assert team.captain_id == 4
    assert _member_ids(engine, team_id) == [3, 4, 5]


def test_keep_refuses_a_non_member_and_an_empty_name(engine: Engine) -> None:
    (team_id,) = _split_teams(engine, [[3, 4]])
    with Session(engine) as session, pytest.raises(Refused, match="Only this team's members can keep it."):
        service.keep(session, session.get_one(Team, team_id), Snowflake(9), "Owls")
    with Session(engine) as session, pytest.raises(Refused, match="A team needs a name."):
        service.keep(session, session.get_one(Team, team_id), Snowflake(3), "   ")


def test_keep_refuses_an_ended_team_and_one_kept_already(engine: Engine) -> None:
    (ended_id,) = _split_teams(engine, [[3, 4]])
    with Session(engine) as session:
        team = session.get_one(Team, ended_id)
        team.ended_at = utc_now()
        session.add(team)
        session.commit()
    with Session(engine) as session, pytest.raises(Refused, match="That team has ended."):
        service.keep(session, session.get_one(Team, ended_id), Snowflake(3), "Owls")

    (kept_id,) = _split_teams(engine, [[3, 4]])
    with Session(engine) as session:
        service.keep(session, session.get_one(Team, kept_id), Snowflake(3), "Owls")
        session.commit()
    with Session(engine) as session, pytest.raises(Refused, match="That team is kept already."):
        service.keep(session, session.get_one(Team, kept_id), Snowflake(4), "Hawks")


def test_end_expired_ends_old_temporary_teams_and_spares_the_rest(engine: Engine) -> None:
    now = datetime(2026, 1, 3, tzinfo=UTC)
    old = _temporary_row(engine, created_at=now - timedelta(days=2))
    young = _temporary_row(engine, created_at=now - timedelta(hours=1))
    lasting = _temporary_row(engine, created_at=now - timedelta(days=2), kind=TeamKind.LASTING)
    solo = _temporary_row(engine, created_at=now - timedelta(days=2), origin=TeamOrigin.SOLO_TOURNAMENT)
    with Session(engine) as session:
        assert service.end_expired(session, now, timedelta(hours=24)) == 1
        session.commit()
    with Session(engine) as session:
        assert session.get_one(Team, old).ended_at is not None
        assert session.get_one(Team, young).ended_at is None
        assert session.get_one(Team, lasting).ended_at is None
        assert session.get_one(Team, solo).ended_at is None


async def test_split_asks_for_members_with_a_user_select(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    options = [InteractionDataOption(name="teams", type=4, value="2")]
    await Teams.split.invoke(
        _cog(engine, discord_client),
        make_interaction("team", options=options, guild_id=GUILD_ID, channel_id=20),
        options,
    )

    data = _response(discord_client)
    assert data["content"] == "Pick the members to split into 2 teams."
    (select,) = data["components"][0]["components"]
    assert select["type"] == 5
    assert select["custom_id"] == "team-split:2"


async def test_picking_members_posts_two_teams_with_a_keep_button_each(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog = _cog(engine, discord_client)
    cog.rng = Random(0)

    await Teams.split_select.invoke(
        cog,
        make_component_interaction("team-split:2", guild_id=GUILD_ID, values=["3", "4", "5"]),
        ["2"],
    )

    data = _response(discord_client)
    assert [field["name"] for field in data["embeds"][0]["fields"]] == ["Team 1", "Team 2"]
    with Session(engine) as session:
        teams = list(session.exec(alive(Team)))
        ids = {team.name: team.id for team in teams}
        members = sorted(member.user_id for team in teams for member in service.members_of(session, team))
    buttons = data["components"][0]["components"]
    assert [button["custom_id"] for button in buttons] == [f"team-keep:{ids['Team 1']}", f"team-keep:{ids['Team 2']}"]
    assert [button["label"] for button in buttons] == ["Keep Team 1", "Keep Team 2"]
    assert members == [3, 4, 5]


async def test_picking_too_few_members_is_refused(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    await Teams.split_select.invoke(
        _cog(engine, discord_client),
        make_component_interaction("team-split:2", guild_id=GUILD_ID, values=["3"]),
        ["2"],
    )

    assert _response(discord_client)["content"] == "Pick at least 2 members for 2 teams."
    with Session(engine) as session:
        assert session.exec(alive(Team)).all() == []


async def test_the_keep_button_refuses_a_non_member(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    (team_id,) = _split_teams(engine, [[INVOKER, 4]])
    await Teams.keep_button.invoke(
        _cog(engine, discord_client),
        make_component_interaction(f"team-keep:{team_id}", guild_id=GUILD_ID, user=_member(9)),
        [str(team_id)],
    )

    assert _response(discord_client)["content"] == "Only this team's members can keep it."


async def test_the_keep_modal_makes_the_team_lasting_for_the_presser(
    engine: Engine,
    make_modal_submit: ModalSubmitFactory,
    discord_client: RecordingClient,
) -> None:
    (team_id,) = _split_teams(engine, [[INVOKER, 4]])
    await Teams.keep_modal.invoke(
        _cog(engine, discord_client),
        make_modal_submit(f"team-keep-name:{team_id}", {"name": "Owls"}, guild_id=GUILD_ID),
        [str(team_id)],
    )

    assert _response(discord_client)["embeds"][0]["description"] == "Kept as **Owls**; you're its captain."
    team = _team_row(engine, team_id)
    assert team.name == "Owls"
    assert team.kind is TeamKind.LASTING
    assert team.captain_id == INVOKER


async def test_the_tick_ends_a_temporary_team_created_two_days_ago(engine: Engine, discord_client: RecordingClient) -> None:
    team_id = _temporary_row(engine, created_at=utc_now() - timedelta(days=2))

    await _cog(engine, discord_client).end_expired_teams()

    assert _team_row(engine, team_id).ended_at is not None


def _statements(session: Session, work: Callable[[], object]) -> int:
    """Count the SQL statements, inserts aside, ``work`` sends through ``session``; the session is flushed after."""
    count = 0

    def counted(*args: object) -> None:
        nonlocal count
        if not str(args[2]).startswith("INSERT"):  # one row each on sqlite; Postgres batches them
            count += 1

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", counted)
    try:
        work()
        session.flush()
    finally:
        event.remove(bind, "before_cursor_execute", counted)
    return count


def test_creating_temporary_teams_takes_the_same_queries_for_any_number_of_groups(engine: Engine) -> None:
    def run(groups: int, size: int) -> int:
        members = [[Snowflake(group * 100 + offset) for offset in range(size)] for group in range(groups)]
        with Session(engine) as session:
            return _statements(session, lambda: service.create_temporary_teams(session, members, TeamOrigin.TEXT_SPLIT))

    assert run(2, 2) == run(20, 5)


def test_disbanding_takes_the_same_queries_for_any_number_of_members(engine: Engine) -> None:
    def run(members: int) -> int:
        team_id = _seed(engine, INVOKER, *[(1000 + offset, offset + 1) for offset in range(members)])
        with Session(engine) as session:
            team = session.get(Team, team_id)
            assert team is not None
            count = _statements(session, lambda: service.disband(session, team, Snowflake(INVOKER)))
            session.commit()
            return count

    assert run(1) == run(20) == 2  # one UPDATE for the memberships, one for the team
    with Session(engine) as session:
        assert session.exec(alive(TeamMember)).all() == []


def test_ending_expired_teams_takes_the_same_queries_for_any_number_of_teams(engine: Engine) -> None:
    now = utc_now() + timedelta(days=5)

    def run(teams: int) -> int:
        with Session(engine) as session:
            service.create_temporary_teams(session, [[Snowflake(offset)] for offset in range(teams)], TeamOrigin.TEXT_SPLIT)
            session.commit()
            count = _statements(session, lambda: service.end_expired(session, now, timedelta(days=1)))
            session.commit()
            return count

    assert run(1) == run(20) == 1  # one UPDATE, with no query first
    with Session(engine) as session:
        assert session.exec(alive(Team).where(Team.ended_at.is_(None))).all() == []  # ty: ignore[unresolved-attribute]


def test_listing_a_users_teams_takes_one_query_for_any_number_of_teams(engine: Engine) -> None:
    def run(teams: int, user: int) -> int:
        for number in range(teams):
            _seed(engine, user, name=f"Crew {user}-{number}")
        with Session(engine) as session:
            return _statements(session, lambda: list(service.teams_of(session, Snowflake(user))))

    assert run(1, 71) == run(20, 72) == 1
