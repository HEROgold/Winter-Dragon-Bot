"""Unit tests: tournament sign-up, team forming, the bracket, drafts and votes, and the /tournament cog (no network)."""

import re
from random import Random
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive, owned_by
from wd_discord.gateway.events import InteractionDataOption
from wd_discord.permissions import Permissions
from wd_errors import Refused

from winter_dragon.cogs.tournament import service
from winter_dragon.cogs.tournament.bracket import first_round, parse_options, round_name, split_into_teams, tally
from winter_dragon.cogs.tournament.cog import Tournaments
from winter_dragon.cogs.tournament.models import (
    DraftChoice,
    DraftKind,
    MatchBallot,
    MatchPhase,
    MatchVote,
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
        guild_id=GUILD_ID,
        channel_id=20,
        organiser_id=ORGANISER,
        name="Cup",
        mode=mode,
        team_size=team_size,
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


def _solo(session: Session, players: int, team_size: int = 1) -> Tournament:
    tournament = _tournament(session, team_size=team_size)
    for user_id in range(100, 100 + players):
        service.sign_up(session, tournament, user_id)
    session.commit()
    return tournament


def _refused(message: str) -> pytest.RaisesExc[Refused]:
    """Expect a refusal with ``message``."""
    return pytest.raises(Refused, match=re.escape(message))


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
        service.sign_up(session, solo, 5)
        session.commit()
        with _refused("You're signed up already."):
            service.sign_up(session, solo, 5)
        captains = _tournament(session, TeamMode.CAPTAINS)
        with pytest.raises(Refused):
            service.sign_up(session, captains, 6)


def test_captains_build_teams_within_the_size(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        service.create_team(session, tournament, 10, "Reds")
        with _refused("A team has that name already."):
            service.create_team(session, tournament, 11, "reds")
        service.add_to_team(session, tournament, 10, 12)
        with _refused("Your team is full: teams have 2 players."):
            service.add_to_team(session, tournament, 10, 13)
        with _refused("Only a team's captain can add players to it."):
            service.add_to_team(session, tournament, 12, 13)
        with _refused("They aren't a player you can remove from your team."):
            service.remove_from_team(session, tournament, 10, 10)
        service.remove_from_team(session, tournament, 10, 12)
        session.commit()
        (team,) = service.teams_of(session, tournament.id or 0)
        assert service.roster(session, team.id or 0) == [10]


def test_a_captain_leaving_disbands_their_team(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=3)
        service.create_team(session, tournament, 10, "Reds")
        service.add_to_team(session, tournament, 10, 12)
        session.commit()
        service.withdraw(session, tournament, 10)
        session.commit()
        assert service.teams_of(session, tournament.id or 0) == []
        assert service.players_of(session, tournament.id or 0) == []


# --- The bracket -----------------------------------------------------------------------------------------------------


def test_start_needs_two_teams(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=3, team_size=2)
        with _refused("I need at least 4 players for two teams of 2."):
            service.start(session, tournament, Random(0))


def test_start_draws_teams_and_gives_byes_their_wins(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=5)
        service.start(session, tournament, Random(0))
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

        with _refused("The match isn't live yet; a team can forfeit, though."):
            service.report(session, tournament, final, winner)
        phases = []
        while final.phase is not MatchPhase.LIVE:
            service.advance(session, final)
            phases.append(final.phase)
        assert phases == [MatchPhase.BAN, MatchPhase.PICK, MatchPhase.LIVE]
        with _refused("Report the winner to finish this match."):
            service.advance(session, final)
        with _refused("That team doesn't play this match."):
            service.report(session, tournament, final, 999)
        service.report(session, tournament, final, winner)

        assert (final.phase, final.winner_id) == (MatchPhase.FINISHED, winner)
        assert (tournament.status, tournament.winner_team_id) == (TournamentStatus.FINISHED, winner)
        with _refused("This match is decided already."):
            service.report(session, tournament, final, winner)


def test_a_forfeit_decides_a_match_before_it_is_live(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=4)
        service.start(session, tournament, Random(0))
        match = _round(session, tournament, 0)[1]
        service.report(session, tournament, match, match.team_b_id or 0, forfeit=True)
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

        with _refused("This match isn't in its ban phase."):
            service.draft(session, match, captain, DraftKind.BAN, "Dust")
        service.advance(session, match)
        with _refused("Only a captain playing this match can ban."):
            service.draft(session, match, teammate, DraftKind.BAN, "Dust")
        service.draft(session, match, captain, DraftKind.BAN, "Dust")
        session.flush()
        with _refused("Dust is banned already."):
            service.draft(session, match, captain, DraftKind.BAN, "Dust")
        assert [draft.value for draft in service.drafts_of(session, match.id or 0)] == ["Dust"]


def test_only_players_vote_and_voting_again_changes_the_answer(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=2)
        service.start(session, tournament, Random(0))
        (match,) = _round(session, tournament, 0)
        vote = service.open_vote(session, match, "Map?", ["Dust", "Mirage"])
        with _refused("Give between 2 and 10 different answers"):
            service.open_vote(session, match, "Map?", ["Dust"])

        with _refused("Only the players of this match can vote."):
            service.cast(session, vote, 999, 0)
        service.cast(session, vote, 100, 0)
        session.flush()
        service.cast(session, vote, 100, 1)
        session.flush()
        assert service.choices_of(session, vote.id or 0) == [1]
        vote.open = False
        with _refused("This vote is closed."):
            service.cast(session, vote, 101, 0)


# --- The cog ---------------------------------------------------------------------------------------------------------


def _cog(engine: Engine, client: RecordingClient) -> Tournaments:
    cog = detached_cog(Tournaments, engine=engine, client=client)
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
        cog,
        make_interaction("tournament", options=options, guild_id=GUILD_ID, channel_id=20),
        options,
    )
    assert _response(discord_client)["data"]["content"] == "You need the Manage Server permission for that."

    interaction = make_interaction(
        "tournament",
        options=options,
        guild_id=GUILD_ID,
        channel_id=20,
        permissions=Permissions.MANAGE_GUILD,
    )
    await Tournaments.create.invoke(cog, interaction, options)

    data = _response(discord_client)["data"]
    (embed,) = data["embeds"]
    assert embed["title"] == "🏆 Cup"
    labels = [button["label"] for button in data["components"][0]["components"]]
    assert labels == ["Join", "Leave", "Participants"]
    with Session(engine) as session:
        assert session.exec(alive(Tournament)).one().organiser_id == ORGANISER


async def test_the_join_button_signs_up_and_refreshes_the_card(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament_id = _tournament(session, team_size=2).id
    cog = _cog(engine, discord_client)

    await Tournaments.join_button.invoke(
        cog,
        make_component_interaction(f"tourney-join:{tournament_id}", guild_id=GUILD_ID),
        [str(tournament_id)],
    )

    update = _response(discord_client)
    assert update["type"] == 7  # UPDATE_MESSAGE
    assert update["data"]["embeds"][0]["fields"][0] == {"name": "Players (1)", "value": "<@3>", "inline": False}
    with Session(engine) as session:
        assert session.exec(alive(TournamentPlayer)).one().user_id == ORGANISER


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
    await Tournaments.match_control.invoke(
        cog,
        make_component_interaction("tourney-match:" + ":".join(args), guild_id=GUILD_ID),
        args,
    )

    assert "wins" in _response(discord_client)["data"]["embeds"][0]["description"]
    followup = discord_client.requests_to("POST", "/webhooks/2/tok")[-1].json
    assert followup["content"] == "🏆 **Cup** is over!"
    with Session(engine) as session:
        assert session.exec(alive(Tournament)).one().winner_team_id == winner


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

    await Tournaments.vote_button.invoke(
        cog,
        make_component_interaction(f"tourney-vote:{vote_id}:0", guild_id=GUILD_ID),
        [str(vote_id), "0"],
    )

    assert _response(discord_client)["data"]["content"] == "Only the players of this match can vote."
    with Session(engine) as session:
        assert session.exec(alive(MatchBallot)).all() == []


@pytest.mark.parametrize("captains", [False, True])
def test_signup_buttons_depend_on_the_team_mode(engine: Engine, discord_client: RecordingClient, *, captains: bool) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS if captains else TeamMode.SOLO)
        _, rows = _cog(engine, discord_client)._signup_card(session, tournament)  # noqa: SLF001
    expected = ["Leave", "Participants"] if captains else ["Join", "Leave", "Participants"]
    assert [button.label for button in rows[0].components] == expected


async def test_the_participants_button_lists_the_teams_to_the_clicker_only(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        service.create_team(session, tournament, 5, "Reds")
        session.commit()
        tournament_id = tournament.id
    cog = _cog(engine, discord_client)

    await Tournaments.participants_button.invoke(
        cog,
        make_component_interaction(f"tourney-participants:{tournament_id}", guild_id=GUILD_ID),
        [str(tournament_id)],
    )

    data = _response(discord_client)["data"]
    assert data["flags"] == 64  # EPHEMERAL
    (embed,) = data["embeds"]
    assert embed["title"] == "🏆 Cup: 1 participant"
    assert embed["description"] == "**Reds** (1/2): <@5>"


def _played_final(session: Session) -> tuple[Tournament, TournamentMatch, int]:
    """Start a two-player solo tournament whose final had a ban and a vote; return it, the final and a captain."""
    tournament = _solo(session, players=2)
    service.start(session, tournament, Random(0))
    (final,) = _round(session, tournament, 0)
    final.phase = MatchPhase.BAN
    (captain,) = service.roster(session, final.team_a_id or 0)
    service.draft(session, final, captain, DraftKind.BAN, "Dust")
    vote = service.open_vote(session, final, "Map?", ["Mirage", "Nuke"])
    service.cast(session, vote, captain, 0)
    session.commit()
    return tournament, final, captain


def test_drafts_votes_and_ballots_belong_to_the_tournaments_guild(engine: Engine) -> None:
    with Session(engine) as session:
        _, _, captain = _played_final(session)

        for model in (DraftChoice, MatchVote, MatchBallot):
            assert len(session.exec(owned_by(model, guild=GUILD_ID)).all()) == 1
            assert session.exec(owned_by(model, guild=GUILD_ID + 1)).all() == []
        assert [ballot.user_id for ballot in session.exec(owned_by(MatchBallot, member=captain, guild=GUILD_ID))] == [captain]
        assert [player.user_id for player in session.exec(owned_by(TournamentPlayer, member=captain))] == [captain]


async def test_join_leave_join_signs_up_once(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament_id = _tournament(session, team_size=2).id or 0
    cog = _cog(engine, discord_client)

    for command in (Tournaments.join, Tournaments.leave, Tournaments.join):
        await command.invoke(cog, make_interaction("tournament", guild_id=GUILD_ID), [])

    with Session(engine) as session:
        assert [player.user_id for player in service.players_of(session, tournament_id)] == [ORGANISER]


async def test_cancel_hides_the_whole_tournament_and_frees_the_guild(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament, _, _ = _played_final(session)
        tournament_id = tournament.id or 0
    cog = _cog(engine, discord_client)

    await Tournaments.cancel_tournament.invoke(cog, make_interaction("tournament", guild_id=GUILD_ID), [])

    with Session(engine) as session:
        assert service.active_tournament(session, GUILD_ID) is None
        assert service.players_of(session, tournament_id) == []
        assert service.teams_of(session, tournament_id) == []
        assert service.matches_of(session, tournament_id) == []
        for model in (Tournament, DraftChoice, MatchVote, MatchBallot):
            assert session.exec(owned_by(model, guild=GUILD_ID)).all() == []
    options = [
        InteractionDataOption(name="name", type=3, value="Rematch"),
        InteractionDataOption(name="team_size", type=4, value=1),
    ]
    interaction = make_interaction(
        "tournament",
        options=options,
        guild_id=GUILD_ID,
        channel_id=20,
        permissions=Permissions.MANAGE_GUILD,
    )
    await Tournaments.create.invoke(cog, interaction, options)
    with Session(engine) as session:
        assert [found.name for found in session.exec(alive(Tournament))] == ["Rematch"]


async def test_vote_takes_the_match_from_a_lookup_value(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        _, final, _ = _played_final(session)
        final_id = final.id
    options = [
        InteractionDataOption(name="match", type=3, value=f"tournamentmatch:{final_id}"),
        InteractionDataOption(name="question", type=3, value="Side?"),
        InteractionDataOption(name="answers", type=3, value="Left, Right"),
    ]
    cog = _cog(engine, discord_client)

    await Tournaments.vote.invoke(cog, make_interaction("tournament", options=options, guild_id=GUILD_ID), options)

    with Session(engine) as session:
        assert sorted(vote.question for vote in session.exec(alive(MatchVote))) == ["Map?", "Side?"]


async def test_vote_refuses_a_match_value_that_is_not_in_the_list(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        _played_final(session)
    options = [
        InteractionDataOption(name="match", type=3, value="1"),
        InteractionDataOption(name="question", type=3, value="Side?"),
        InteractionDataOption(name="answers", type=3, value="Left, Right"),
    ]
    cog = _cog(engine, discord_client)

    await Tournaments.vote.invoke(cog, make_interaction("tournament", options=options, guild_id=GUILD_ID), options)

    assert _response(discord_client)["data"]["content"] == "I can't find that match; pick one from the list."


async def test_match_card_takes_the_match_from_a_lookup_value(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        _, final, _ = _played_final(session)
        final_id = final.id
    options = [InteractionDataOption(name="match", type=3, value=f"tournamentmatch:{final_id}")]
    cog = _cog(engine, discord_client)

    await Tournaments.match_card.invoke(cog, make_interaction("tournament", options=options, guild_id=GUILD_ID), options)

    (embed,) = _response(discord_client)["data"]["embeds"]
    assert "Dust" in str(embed)


async def test_match_card_refuses_a_match_when_the_guild_has_no_tournament(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        _, final, _ = _played_final(session)
        final_id = final.id
    options = [InteractionDataOption(name="match", type=3, value=f"tournamentmatch:{final_id}")]
    cog = _cog(engine, discord_client)

    await Tournaments.match_card.invoke(
        cog,
        make_interaction("tournament", options=options, guild_id=GUILD_ID + 1),
        options,
    )

    assert _response(discord_client)["data"]["content"].startswith("There's no tournament here;")
