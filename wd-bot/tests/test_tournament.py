"""Unit tests: tournament sign-up, team forming, the bracket, drafts and votes, and the /tournament cog (no network)."""

from __future__ import annotations

from random import Random
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, select
from wd_bot.registry import CommandRegistry
from wd_discord.permissions import Permissions

from winter_dragon.cogs.tournament import service
from winter_dragon.cogs.tournament.bracket import first_round, parse_options, round_name, split_into_teams, tally
from winter_dragon.cogs.tournament.cog import Tournaments
from winter_dragon.cogs.tournament.models import (
    DraftKind,
    MatchBallot,
    MatchPhase,
    TeamMode,
    Tournament,
    TournamentMatch,
    TournamentPlayer,
    TournamentStatus,
    TournamentTeam,
)


if TYPE_CHECKING:
    from conftest import ComponentInteractionFactory, InteractionFactory
    from sqlalchemy import Engine
    from wd_discord.testing import RecordingClient


GUILD_ID = 1
ORGANISER = 3
"""The default invoking user of the interaction fixtures."""


def _tournament(session: Session, mode: TeamMode = TeamMode.SOLO, team_size: int = 1) -> Tournament:
    tournament = Tournament(
        guild_id=GUILD_ID, channel_id=20, organiser_id=ORGANISER, name="Cup", mode=mode, team_size=team_size
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


def _solo(session: Session, players: int, team_size: int = 1) -> Tournament:
    tournament = _tournament(session, team_size=team_size)
    for user_id in range(100, 100 + players):
        assert service.sign_up(session, tournament, user_id) is None
    session.commit()
    return tournament


def _round(session: Session, tournament: Tournament, round_: int) -> list[TournamentMatch]:
    return [match for match in service.matches_of(session, tournament.id or 0) if match.round == round_]


# --- Pure bracket arithmetic -----------------------------------------------------------------------------------------


def test_split_into_teams_spreads_leftover_players() -> None:
    teams = split_into_teams(list(range(7)), 2, Random(0))
    assert sorted(len(team) for team in teams) == [2, 2, 3]
    assert sorted(user for team in teams for user in team) == list(range(7))
    assert split_into_teams([1, 2, 3], 2, Random(0)) == []


def test_first_round_gives_byes_to_top_seeds_and_never_pairs_two_byes() -> None:
    assert first_round([1, 2, 3, 4, 5]) == [(1, None), (2, None), (3, None), (4, 5)]
    assert first_round([1, 2]) == [(1, 2)]


def test_round_names_count_back_from_the_final() -> None:
    assert [round_name(round_, 4) for round_ in range(4)] == ["Round 1", "Quarter-finals", "Semi-finals", "Final"]


def test_vote_options_and_tally() -> None:
    assert parse_options(" Dust, Mirage ,, dust, Dust ") == ["Dust", "Mirage", "dust"]
    assert tally(3, [0, 2, 2, 7, -1]) == [1, 0, 2]


# --- Sign-up and teams -----------------------------------------------------------------------------------------------


def test_solo_sign_up_refuses_twice_and_captains_tournaments(engine: Engine) -> None:
    with Session(engine) as session:
        solo = _tournament(session)
        assert service.sign_up(session, solo, 5) is None
        session.commit()
        assert service.sign_up(session, solo, 5) == "You're signed up already."
        captains = _tournament(session, TeamMode.CAPTAINS)
        assert service.sign_up(session, captains, 6) is not None


def test_captains_build_teams_within_the_size(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        assert service.create_team(session, tournament, 10, "Reds") is None
        assert service.create_team(session, tournament, 11, "reds") == "A team has that name already."
        assert service.add_to_team(session, tournament, 10, 12) is None
        assert service.add_to_team(session, tournament, 10, 13) == "Your team is full: teams have 2 players."
        assert service.add_to_team(session, tournament, 12, 13) == "Only a team's captain can add players to it."
        assert service.remove_from_team(session, tournament, 10, 10) == "They aren't a player you can remove from your team."
        assert service.remove_from_team(session, tournament, 10, 12) is None
        session.commit()
        (team,) = service.teams_of(session, tournament.id or 0)
        assert service.roster(session, team.id or 0) == [10]


def test_a_captain_leaving_disbands_their_team(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=3)
        service.create_team(session, tournament, 10, "Reds")
        service.add_to_team(session, tournament, 10, 12)
        session.commit()
        assert service.withdraw(session, tournament, 10) is None
        session.commit()
        assert service.teams_of(session, tournament.id or 0) == []
        assert service.players_of(session, tournament.id or 0) == []


# --- The bracket -----------------------------------------------------------------------------------------------------


def test_start_needs_two_teams(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=3, team_size=2)
        assert service.start(session, tournament, Random(0)) == "I need at least 4 players for two teams of 2."


def test_start_draws_teams_and_gives_byes_their_wins(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=5)
        assert service.start(session, tournament, Random(0)) is None
        session.commit()

        assert tournament.status is TournamentStatus.RUNNING
        assert len(service.teams_of(session, tournament.id or 0)) == 5
        assert all(player.team_id is not None for player in service.players_of(session, tournament.id or 0))
        first = _round(session, tournament, 0)
        assert [match.phase for match in first] == [MatchPhase.FINISHED] * 3 + [MatchPhase.READY]
        semis = _round(session, tournament, 1)
        assert semis[0].phase is MatchPhase.READY  # both bye winners arrived
        assert semis[1].team_a_id is not None
        assert semis[1].team_b_id is None
        assert len(_round(session, tournament, 2)) == 1


def test_a_match_moves_through_its_phases_and_the_final_crowns_a_champion(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=2)
        service.start(session, tournament, Random(0))
        (final,) = _round(session, tournament, 0)
        winner = final.team_a_id or 0

        assert service.report(session, tournament, final, winner) == "The match isn't live yet; a team can forfeit, though."
        phases = []
        while service.advance(session, final) is None:
            phases.append(final.phase)
        assert phases == [MatchPhase.BAN, MatchPhase.PICK, MatchPhase.LIVE]
        assert service.advance(session, final) == "Report the winner to finish this match."
        assert service.report(session, tournament, final, 999) == "That team doesn't play this match."
        assert service.report(session, tournament, final, winner) is None

        assert (final.phase, final.winner_id) == (MatchPhase.FINISHED, winner)
        assert (tournament.status, tournament.winner_team_id) == (TournamentStatus.FINISHED, winner)
        assert service.report(session, tournament, final, winner) == "This match is decided already."


def test_a_forfeit_decides_a_match_before_it_is_live(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=4)
        service.start(session, tournament, Random(0))
        match = _round(session, tournament, 0)[1]
        assert service.report(session, tournament, match, match.team_b_id or 0, forfeit=True) is None
        assert match.phase is MatchPhase.FORFEIT
        (final,) = _round(session, tournament, 1)
        assert final.team_b_id == match.team_b_id


# --- Drafts and votes ------------------------------------------------------------------------------------------------


def test_only_a_playing_captain_drafts_in_the_right_phase(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=4, team_size=2)
        service.start(session, tournament, Random(0))
        (match,) = _round(session, tournament, 0)
        team_a = session.get(TournamentTeam, match.team_a_id)
        assert team_a is not None
        captain = team_a.captain_id
        teammate = next(user for user in service.roster(session, team_a.id or 0) if user != captain)

        assert service.draft(session, match, captain, DraftKind.BAN, "Dust") == "This match isn't in its ban phase."
        service.advance(session, match)
        assert service.draft(session, match, teammate, DraftKind.BAN, "Dust") == "Only a captain playing this match can ban."
        assert service.draft(session, match, captain, DraftKind.BAN, "Dust") is None
        session.flush()
        assert service.draft(session, match, captain, DraftKind.BAN, "Dust") == "Dust is banned already."
        assert [draft.value for draft in service.drafts_of(session, match.id or 0)] == ["Dust"]


def test_only_players_vote_and_voting_again_changes_the_answer(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=2)
        service.start(session, tournament, Random(0))
        (match,) = _round(session, tournament, 0)
        vote = service.open_vote(session, match, "Map?", ["Dust", "Mirage"])
        assert not isinstance(vote, str)
        assert service.open_vote(session, match, "Map?", ["Dust"]) != vote

        assert service.cast(session, vote, 999, 0) == "Only the players of this match can vote."
        assert service.cast(session, vote, 100, 0) is None
        session.flush()
        assert service.cast(session, vote, 100, 1) is None
        session.flush()
        assert service.choices_of(session, vote.id or 0) == [1]
        vote.open = False
        assert service.cast(session, vote, 101, 0) == "This vote is closed."


# --- The cog ---------------------------------------------------------------------------------------------------------


def _cog(engine: Engine, client: RecordingClient) -> Tournaments:
    cog = Tournaments.__new__(Tournaments)
    cog.bot = SimpleNamespace(client=client, registry=CommandRegistry())  # pyright: ignore[reportAttributeAccessIssue]
    cog.session = Session(engine)
    cog.rng = Random(0)
    return cog


def _response(discord_client: RecordingClient) -> dict[str, object]:
    return discord_client.interaction_responses()[-1]


async def test_create_needs_manage_server_and_posts_a_signup_card(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    from wd_discord.gateway.events import InteractionDataOption  # noqa: PLC0415

    options = [
        InteractionDataOption(name="name", type=3, value="Cup"),
        InteractionDataOption(name="team_size", type=4, value=2),
    ]
    cog = _cog(engine, discord_client)
    await Tournaments.create.invoke(
        cog, make_interaction("tournament", options=options, guild_id=GUILD_ID, channel_id=20), options
    )
    assert _response(discord_client)["data"]["content"] == "You need the Manage Server permission to open a tournament."  # pyright: ignore[reportIndexIssue]

    interaction = make_interaction(
        "tournament", options=options, guild_id=GUILD_ID, channel_id=20, permissions=Permissions.MANAGE_GUILD
    )
    await Tournaments.create.invoke(cog, interaction, options)

    data = _response(discord_client)["data"]
    (embed,) = data["embeds"]  # pyright: ignore[reportIndexIssue]
    assert embed["title"] == "🏆 Cup"
    labels = [button["label"] for button in data["components"][0]["components"]]  # pyright: ignore[reportIndexIssue]
    assert labels == ["Join", "Leave"]
    with Session(engine) as session:
        assert session.exec(select(Tournament)).one().organiser_id == ORGANISER


async def test_the_join_button_signs_up_and_refreshes_the_card(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament_id = _tournament(session, team_size=2).id
    cog = _cog(engine, discord_client)

    await Tournaments.join_button.invoke(cog, make_component_interaction(f"tourney-join:{tournament_id}"), [str(tournament_id)])

    update = _response(discord_client)
    assert update["type"] == 7  # UPDATE_MESSAGE
    assert update["data"]["embeds"][0]["fields"][0] == {"name": "Players (1)", "value": "<@3>", "inline": False}  # pyright: ignore[reportIndexIssue]
    with Session(engine) as session:
        assert session.exec(select(TournamentPlayer)).one().user_id == ORGANISER


async def test_the_organiser_reports_the_final_winner_from_the_match_card(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=2)
        service.start(session, tournament, Random(0))
        (final,) = _round(session, tournament, 0)
        final.phase = MatchPhase.LIVE
        session.add(final)
        session.commit()
        match_id, winner = final.id, final.team_a_id
    cog = _cog(engine, discord_client)

    args = [str(match_id), "win", str(winner)]
    await Tournaments.match_control.invoke(cog, make_component_interaction("tourney-match:" + ":".join(args)), args)

    assert "wins" in _response(discord_client)["data"]["embeds"][0]["description"]  # pyright: ignore[reportIndexIssue]
    followup = discord_client.requests_to("POST", "/webhooks/2/tok")[-1].json
    assert followup["content"] == "🏆 **Cup** is over!"
    with Session(engine) as session:
        assert session.exec(select(Tournament)).one().winner_team_id == winner


async def test_only_match_players_can_use_the_vote_buttons(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=2)
        service.start(session, tournament, Random(0))
        (final,) = _round(session, tournament, 0)
        vote = service.open_vote(session, final, "Map?", ["Dust", "Mirage"])
        assert not isinstance(vote, str)
        session.commit()
        vote_id = vote.id
    cog = _cog(engine, discord_client)

    await Tournaments.vote_button.invoke(cog, make_component_interaction(f"tourney-vote:{vote_id}:0"), [str(vote_id), "0"])

    assert _response(discord_client)["data"]["content"] == "Only the players of this match can vote."  # pyright: ignore[reportIndexIssue]
    with Session(engine) as session:
        assert session.exec(select(MatchBallot)).all() == []


@pytest.mark.parametrize("captains", [False, True])
def test_signup_buttons_depend_on_the_team_mode(engine: Engine, discord_client: RecordingClient, *, captains: bool) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS if captains else TeamMode.SOLO)
        _, rows = _cog(engine, discord_client)._signup_card(session, tournament)  # noqa: SLF001
    assert [button.label for button in rows[0].components] == (["Leave"] if captains else ["Join", "Leave"])
