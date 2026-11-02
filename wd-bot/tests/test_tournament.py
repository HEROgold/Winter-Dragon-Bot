"""Unit tests: tournament sign-up, team forming, the bracket, drafts and votes, and the /tournament cog (no network)."""

import re
from random import Random
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_bot.commands import Lookup
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import DELETED_MEMBER, alive, owned_by
from wd_discord import AutocompleteInteraction
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import InteractionData, InteractionDataOption, InteractionType, ResolvedData
from wd_discord.permissions import Permissions
from wd_discord.resources.user import User
from wd_discord.testing import message_json, user_json
from wd_discord.snowflake import Snowflake
from wd_errors import Refused
from wd_types.clock import utc_now

from winter_dragon.cogs.privacy.domain import hide_member_data
from winter_dragon.cogs.team import service as team_service
from winter_dragon.cogs.team.models import Team, TeamKind, TeamOrigin
from winter_dragon.cogs.team.split import split_into_teams
from winter_dragon.cogs.tournament import service
from winter_dragon.cogs.tournament.bracket import first_round, parse_options, round_name, tally
from winter_dragon.cogs.tournament.cog import Tournaments
from winter_dragon.cogs.tournament.models import (
    DraftChoice,
    DraftKind,
    EntryPlayer,
    MatchBallot,
    MatchLineup,
    MatchPhase,
    MatchVote,
    TeamMode,
    Tournament,
    TournamentEntry,
    TournamentMatch,
    TournamentPost,
    TournamentSignup,
    TournamentStatus,
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
        organiser_id=ORGANISER,
        name="Cup",
        mode=mode,
        team_size=team_size,
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


def _named(
    session: Session,
    name: str,
    *,
    organiser_id: int = 50,
    guild_id: int = GUILD_ID,
    status: TournamentStatus = TournamentStatus.SIGNUP,
) -> Tournament:
    tournament = Tournament(
        guild_id=guild_id, organiser_id=organiser_id, name=name, mode=TeamMode.SOLO, team_size=1, status=status
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


def _pick(tournament: Tournament) -> InteractionDataOption:
    """The ``tournament`` option as the autocomplete suggests it for ``tournament``; read it while its session is open."""
    return InteractionDataOption(name="tournament", type=3, value=Lookup.choice(tournament, tournament.name).value)


def _solo(session: Session, players: int, team_size: int = 1) -> Tournament:
    tournament = _tournament(session, team_size=team_size)
    for user_id in range(100, 100 + players):
        service.sign_up(session, tournament, user_id)
    session.commit()
    return tournament


def _entered(session: Session, tournament: Tournament, captain_id: int, name: str) -> TournamentEntry:
    """Create the lasting team ``name`` captained by ``captain_id``, and enter it into ``tournament``."""
    team = team_service.create_team(session, name, captain_id)
    session.commit()
    entry = service.enter(session, tournament, team, captain_id)
    session.commit()
    return entry


def _refused(message: str) -> pytest.RaisesExc[Refused]:
    """Expect a refusal with ``message``."""
    return pytest.raises(Refused, match=re.escape(message))


def _round(session: Session, tournament: Tournament, round_: int) -> list[TournamentMatch]:
    return [match for match in service.matches_of(session, tournament.id or 0) if match.round == round_]


def _finish(session: Session, tournament: Tournament) -> None:
    """Play the tournament's final, live, to its end, with the first team of the final winning."""
    final = service.matches_of(session, tournament.id or 0)[-1]
    final.phase = MatchPhase.LIVE
    session.add(final)
    session.commit()
    service.report(session, tournament, final, final.entry_a_id or 0)
    session.commit()


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
        reds = _entered(session, tournament, 10, "Reds")
        team_service.join(session, session.get_one(Team, reds.team_id), 12)
        session.commit()
        service.add_player(session, tournament, reds, 10, 12)
        with _refused("Only a team's captain can change its entry."):
            service.add_player(session, tournament, reds, 12, 12)
        with _refused("They're in this entry already."):
            service.add_player(session, tournament, reds, 10, 12)
        with _refused("They aren't a player you can remove from your entry."):
            service.remove_player(session, tournament, reds, 10, 10)
        service.remove_player(session, tournament, reds, 10, 12)
        session.commit()
        assert service.roster(session, reds.id or 0) == [10]


def test_enter_refuses_a_temporary_team_a_non_captain_a_second_entry_and_a_duplicate_name(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS)
        (temporary,) = team_service.create_temporary_teams(session, [[20, 21]], TeamOrigin.SOLO_TOURNAMENT)
        with _refused("Only the team's captain can enter it."):
            service.enter(session, tournament, temporary, 20)
        reds = team_service.create_team(session, "Reds", 10)
        with _refused("Only the team's captain can enter it."):
            service.enter(session, tournament, reds, 11)
        service.enter(session, tournament, reds, 10)
        session.commit()
        with _refused("That team has entered already."):
            service.enter(session, tournament, reds, 10)
        blues = team_service.create_team(session, "reds", 11)
        with _refused("An entry has that name already."):
            service.enter(session, tournament, blues, 11)


def test_add_player_refuses_someone_outside_the_team_and_a_full_entry(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        team = session.get_one(Team, reds.team_id)
        team_service.join(session, team, 12)
        session.commit()
        with _refused("They aren't in your team."):
            service.add_player(session, tournament, reds, 10, 13)
        service.add_player(session, tournament, reds, 10, 12)
        team_service.join(session, team, 13)
        session.commit()
        with _refused("Your entry is full: entries have 2 players."):
            service.add_player(session, tournament, reds, 10, 13)


def test_a_member_can_play_for_two_entries_of_one_tournament(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        blues = _entered(session, tournament, 11, "Blues")
        for entry, captain_id in ((reds, 10), (blues, 11)):
            team_service.join(session, session.get_one(Team, entry.team_id), 12)
            session.commit()
            service.add_player(session, tournament, entry, captain_id, 12)
            session.commit()
        assert service.roster(session, reds.id or 0) == [10, 12]
        assert service.roster(session, blues.id or 0) == [11, 12]
        assert service.entry_of_captain(session, tournament, 11) == blues


def test_hiding_a_member_withdraws_only_the_entries_left_without_players(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        blues = _entered(session, tournament, 11, "Blues")
        team_service.join(session, session.get_one(Team, blues.team_id), 10)
        session.commit()
        service.add_player(session, tournament, blues, 11, 10)
        session.commit()

        service.WithdrawHiddenMember.on_member_hidden(session, Snowflake(10))
        session.commit()

        assert [entry.name for entry in service.entries_of(session, tournament.id or 0)] == ["Blues"]
        assert service.roster(session, blues.id or 0) == [11]


def test_a_captain_leaving_withdraws_their_entry(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=3)
        reds = _entered(session, tournament, 10, "Reds")
        team_service.join(session, session.get_one(Team, reds.team_id), 12)
        session.commit()
        service.add_player(session, tournament, reds, 10, 12)
        session.commit()
        service.withdraw(session, tournament, 10)
        session.commit()
        assert service.entries_of(session, tournament.id or 0) == []
        assert session.exec(alive(EntryPlayer)).all() == []
        assert session.get_one(Team, reds.team_id).ended_at is None


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
        assert len(service.entries_of(session, tournament.id or 0)) == 5
        assert len(session.exec(alive(EntryPlayer)).all()) == 5
        first = _round(session, tournament, 0)
        assert [match.phase for match in first] == [MatchPhase.FINISHED] * 3 + [MatchPhase.READY]
        semis = _round(session, tournament, 1)
        assert semis[0].phase is MatchPhase.READY  # both bye winners arrived
        assert semis[1].entry_a_id is not None
        assert semis[1].entry_b_id is None
        assert len(_round(session, tournament, 2)) == 1


def test_a_match_moves_through_its_phases_and_the_final_crowns_a_champion(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=2)
        service.start(session, tournament, Random(0))
        (final,) = _round(session, tournament, 0)
        winner = final.entry_a_id or 0

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
        assert (tournament.status, tournament.winner_entry_id) == (TournamentStatus.FINISHED, winner)
        with _refused("This match is decided already."):
            service.report(session, tournament, final, winner)


def test_a_forfeit_decides_a_match_before_it_is_live(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=4)
        service.start(session, tournament, Random(0))
        match = _round(session, tournament, 0)[1]
        service.report(session, tournament, match, match.entry_b_id or 0, forfeit=True)
        assert match.phase is MatchPhase.FORFEIT
        (final,) = _round(session, tournament, 1)
        assert final.entry_b_id == match.entry_b_id


# --- Drafts and votes ------------------------------------------------------------------------------------------------


def test_only_a_playing_captain_drafts_in_the_right_phase(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=4, team_size=2)
        service.start(session, tournament, Random(0))
        (match,) = _round(session, tournament, 0)
        entry_a = session.get(TournamentEntry, match.entry_a_id)
        assert entry_a is not None
        captain = session.get_one(Team, entry_a.team_id).captain_id or 0
        teammate = next(user for user in service.roster(session, entry_a.id or 0) if user != captain)

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
    discord_client.reply("POST", "/channels/20/messages", message_json(id="200", channel_id="20"))
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

    (post,) = discord_client.requests_to("POST", "/channels/20/messages")
    (embed,) = post.json["embeds"]
    assert embed["title"] == "🏆 Cup"
    labels = [button["label"] for button in post.json["components"][0]["components"]]
    assert labels == ["Join", "Leave", "Participants"]
    assert _response(discord_client)["data"]["embeds"][0]["description"] == "**Cup** is open for sign-up."
    with Session(engine) as session:
        assert session.exec(alive(Tournament)).one().organiser_id == ORGANISER
        (row,) = session.exec(alive(TournamentPost)).all()
        assert (row.channel_id, row.message_id) == (20, 200)


async def test_a_guild_can_run_two_tournaments_at_once(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("POST", "/channels/20/messages", message_json(id="200", channel_id="20"))
    cog = _cog(engine, discord_client)
    for name in ("Cup", "League"):
        options = [InteractionDataOption(name="name", type=3, value=name)]
        interaction = make_interaction(
            "tournament",
            options=options,
            guild_id=GUILD_ID,
            channel_id=20,
            permissions=Permissions.MANAGE_GUILD,
        )
        await Tournaments.create.invoke(cog, interaction, options)

    with Session(engine) as session:
        assert sorted(found.name for found in session.exec(alive(Tournament))) == ["Cup", "League"]


async def test_post_shows_a_tournament_in_this_channel_and_refuses_another_server(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("POST", "/channels/21/messages", message_json(id="210", channel_id="21"))
    with Session(engine) as session:
        tournament = _named(session, "Cup", organiser_id=ORGANISER)
        foreign = _named(session, "Foreign", guild_id=GUILD_ID + 1, organiser_id=ORGANISER)
        tournament_id = tournament.id or 0
        options = [_pick(tournament)]
        foreign_options = [_pick(foreign)]
    cog = _cog(engine, discord_client)

    await Tournaments.post_tournament.invoke(
        cog,
        make_interaction(
            "tournament", options=options, guild_id=GUILD_ID, channel_id=21, permissions=Permissions.MANAGE_MESSAGES
        ),
        options,
    )

    assert _response(discord_client)["data"]["embeds"][0]["description"] == "Posted **Cup** here."
    with Session(engine) as session:
        (row,) = session.exec(alive(TournamentPost)).all()
        assert (row.tournament_id, row.channel_id, row.message_id) == (tournament_id, 21, 210)

    await Tournaments.post_tournament.invoke(
        cog,
        make_interaction(
            "tournament",
            options=foreign_options,
            guild_id=GUILD_ID,
            channel_id=21,
            permissions=Permissions.MANAGE_MESSAGES,
        ),
        foreign_options,
    )

    assert _response(discord_client)["data"]["content"] == "That tournament belongs to another server."
    assert len(discord_client.requests_to("POST", "/channels/21/messages")) == 1


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
        assert session.exec(alive(TournamentSignup)).one().user_id == ORGANISER


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
        match_id, winner = final.id, final.entry_a_id
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
        assert session.exec(alive(Tournament)).one().winner_entry_id == winner


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
        _entered(session, tournament, 5, "Reds")
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
    (captain,) = service.roster(session, final.entry_a_id or 0)
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
        assert [player.user_id for player in session.exec(owned_by(EntryPlayer, member=captain))] == [captain]


async def test_join_leave_join_signs_up_once(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, team_size=2)
        tournament_id = tournament.id or 0
        options = [_pick(tournament)]
    cog = _cog(engine, discord_client)

    for command in (Tournaments.join, Tournaments.leave, Tournaments.join):
        await command.invoke(cog, make_interaction("tournament", options=options, guild_id=GUILD_ID), options)

    with Session(engine) as session:
        assert [signup.user_id for signup in service.signups_of(session, tournament_id)] == [ORGANISER]


async def test_cancel_hides_the_tournament(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        tournament, _, _ = _played_final(session)
        tournament_id = tournament.id or 0
        options = [_pick(tournament)]
    cog = _cog(engine, discord_client)

    await Tournaments.cancel_tournament.invoke(cog, make_interaction("tournament", options=options, guild_id=GUILD_ID), options)

    with Session(engine) as session:
        assert list(service.visible_tournaments(session, GUILD_ID, ORGANISER, None)) == []
        assert service.signups_of(session, tournament_id) == []
        assert service.entries_of(session, tournament_id) == []
        assert service.matches_of(session, tournament_id) == []
        for model in (Tournament, DraftChoice, MatchVote, MatchBallot):
            assert session.exec(owned_by(model, guild=GUILD_ID)).all() == []


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


async def test_match_card_refuses_a_match_of_another_server(
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

    assert _response(discord_client)["data"]["content"] == "That tournament belongs to another server."


def _autocomplete(client: RecordingClient) -> AutocompleteInteraction:
    """An autocomplete interaction from the organiser in ``GUILD_ID``, typing into the tournament option."""
    model = AutocompleteInteractionModel(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE,
        token="tok",  # noqa: S106
        version=1,
        guild_id=str(GUILD_ID),
        user=User.model_validate(user_json(id=str(ORGANISER), username="organiser")),
        data=InteractionData(id="10", name="tournament", type=1),
    )
    return AutocompleteInteraction(client, model)


async def test_tournament_choices_suggests_the_visible_tournaments_that_match(
    engine: Engine,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        _named(session, "Spring Cup", organiser_id=ORGANISER)
        _named(session, "Autumn Cup", organiser_id=ORGANISER)
        _named(session, "Winter League", organiser_id=ORGANISER)
        _named(session, "Hidden Cup")
    cog = _cog(engine, discord_client)

    choices = await cog.tournament_choices(_autocomplete(discord_client), "cup")

    assert sorted(choice.name for choice in choices) == ["Autumn Cup", "Spring Cup"]


async def test_the_join_button_edits_every_post_of_the_tournament(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("PATCH", "/channels/20/messages/200", message_json(id="200", channel_id="20"))
    discord_client.reply("PATCH", "/channels/21/messages/210", message_json(id="210", channel_id="21"))
    with Session(engine) as session:
        tournament = _tournament(session, team_size=2)
        service.add_post(session, tournament, 20, 200)
        service.add_post(session, tournament, 21, 210)
        session.commit()
        tournament_id = tournament.id
    cog = _cog(engine, discord_client)

    await Tournaments.join_button.invoke(
        cog,
        make_component_interaction(f"tourney-join:{tournament_id}", guild_id=GUILD_ID),
        [str(tournament_id)],
    )

    for channel_id, message_id in ((20, 200), (21, 210)):
        (edit,) = discord_client.requests_to("PATCH", f"/channels/{channel_id}/messages/{message_id}")
        assert edit.json["embeds"][0]["fields"][0]["name"] == "Players (1)"


def test_visible_tournaments_are_the_organisers_signed_up_and_posted_ones(engine: Engine) -> None:
    with Session(engine) as session:
        _named(session, "Organised", organiser_id=ORGANISER)
        signed_up = _named(session, "Signed")
        service.sign_up(session, signed_up, ORGANISER)
        posted = _named(session, "Posted")
        service.add_post(session, posted, 20, 200)
        _named(session, "Hidden")
        _named(session, "Finished", organiser_id=ORGANISER, status=TournamentStatus.FINISHED)
        _named(session, "Elsewhere", guild_id=GUILD_ID + 1, organiser_id=ORGANISER)
        session.commit()

        assert [found.name for found in service.visible_tournaments(session, GUILD_ID, ORGANISER, 99)] == [
            "Organised",
            "Signed",
        ]
        assert [found.name for found in service.visible_tournaments(session, GUILD_ID, 7, 20)] == ["Posted"]


# --- Solo teams and their ends ---------------------------------------------------------------------------------------


def test_a_solo_start_makes_temporary_teams_with_their_first_drawn_captains(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _solo(session, players=4, team_size=2)
        service.start(session, tournament, Random(0))
        session.commit()

        teams = list(session.exec(alive(Team).where(Team.origin == TeamOrigin.SOLO_TOURNAMENT)))
        entries = service.entries_of(session, tournament.id or 0)
        assert len(teams) == len(entries) == 2
        assert all(team.kind is TeamKind.TEMPORARY and team.ended_at is None for team in teams)
        for entry in entries:
            team = session.get_one(Team, entry.team_id)
            assert entry.name == team.name
            assert team.captain_id == service.roster(session, entry.id or 0)[0]
        players = [user for entry in entries for user in service.roster(session, entry.id or 0)]
        assert sorted(players) == [100, 101, 102, 103]


def test_finishing_and_cancelling_end_a_solo_tournaments_temporary_teams(engine: Engine) -> None:
    with Session(engine) as session:
        finished = _solo(session, players=2)
        service.start(session, finished, Random(0))
        session.commit()
        _finish(session, finished)
        assert [team.ended_at is not None for team in session.exec(alive(Team))] == [True, True]

        cancelled = _solo(session, players=2)
        service.start(session, cancelled, Random(0))
        session.commit()
        service.cancel(session, cancelled)
        session.commit()
        assert [team.ended_at is not None for team in session.exec(alive(Team))] == [True, True, True, True]


def test_a_lasting_team_stays_unended_when_its_tournament_ends(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS)
        reds = _entered(session, tournament, 10, "Reds")
        blues = _entered(session, tournament, 11, "Blues")
        service.start(session, tournament, Random(0))
        session.commit()
        _finish(session, tournament)

        assert tournament.status is TournamentStatus.FINISHED
        assert [session.get_one(Team, entry.team_id).ended_at for entry in (reds, blues)] == [None, None]


async def test_entry_add_refuses_a_player_who_is_not_in_the_server(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("GET", f"/guilds/{GUILD_ID}/members/4", {"code": 10007, "message": "Unknown Member"}, status=404)
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        _entered(session, tournament, ORGANISER, "Reds")
        pick = _pick(tournament)
    player = InteractionDataOption(name="player", type=6, value="4")
    resolved = ResolvedData(users={"4": User.model_validate({"id": "4", "username": "user4", "discriminator": "0"})})
    options = [pick, player]
    cog = _cog(engine, discord_client)

    await Tournaments.entry_add.invoke(
        cog,
        make_interaction("tournament", options=options, resolved=resolved, guild_id=GUILD_ID),
        options,
    )

    assert _response(discord_client)["data"]["content"] == "They aren't in this server, so they can't play in its tournament."
    with Session(engine) as session:
        assert session.exec(alive(EntryPlayer)).one().user_id == ORGANISER


# --- Lineups and clashes ---------------------------------------------------------------------------------------------


def _add_to_entry(session: Session, tournament: Tournament, entry: TournamentEntry, captain_id: int, user_id: int) -> None:
    """Make ``user_id`` a member of the entry's team, then add them to the entry as its captain."""
    team_service.join(session, session.get_one(Team, entry.team_id), user_id)
    session.commit()
    service.add_player(session, tournament, entry, captain_id, user_id)
    session.commit()


def _play(session: Session, tournament: Tournament, match: TournamentMatch, winner_id: int) -> None:
    """Play ``match`` live to a win for ``winner_id``, skipping its draft."""
    match.phase = MatchPhase.LIVE
    session.add(match)
    session.commit()
    service.report(session, tournament, match, winner_id)
    session.commit()


def _undecided_match(session: Session, tournament: Tournament, entry: TournamentEntry) -> TournamentMatch:
    """Return the lowest-round match of ``entry`` that isn't decided."""
    return next(
        match
        for match in service.matches_of(session, tournament.id or 0)
        if not match.phase.decided and entry.id in (match.entry_a_id, match.entry_b_id)
    )


def test_a_match_copies_its_entries_players_into_its_lineup_once_ready(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        _add_to_entry(session, tournament, reds, 10, 20)
        _entered(session, tournament, 11, "Blues")
        _entered(session, tournament, 12, "Greens")
        _entered(session, tournament, 13, "Golds")
        service.start(session, tournament, Random(0))
        session.commit()

        for match in _round(session, tournament, 0):
            assert match.phase is MatchPhase.READY
            for entry_id in (match.entry_a_id or 0, match.entry_b_id or 0):
                assert service.lineup(session, match.id or 0, entry_id) == service.roster(session, entry_id)
        (final,) = _round(session, tournament, 1)
        assert final.phase is MatchPhase.WAITING
        assert service.lineup(session, final.id or 0, reds.id or 0) == []

        for match in _round(session, tournament, 0):
            _play(session, tournament, match, match.entry_a_id or 0)
        (final,) = _round(session, tournament, 1)
        assert final.phase is MatchPhase.READY
        for entry_id in (final.entry_a_id or 0, final.entry_b_id or 0):
            assert service.lineup(session, final.id or 0, entry_id) == service.roster(session, entry_id)


def test_a_lineup_change_reaches_the_next_match_not_yet_live_and_later_ones(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        _add_to_entry(session, tournament, reds, 10, 20)
        _entered(session, tournament, 11, "Blues")
        _entered(session, tournament, 12, "Greens")
        _entered(session, tournament, 13, "Golds")
        service.start(session, tournament, Random(0))
        session.commit()
        match = _undecided_match(session, tournament, reds)
        match_id, reds_id = match.id or 0, reds.id or 0

        # 21 isn't in the team, so a stand-in is allowed.
        service.change_lineup(session, tournament, reds, 10, 20, playing=False)
        service.change_lineup(session, tournament, reds, 10, 21, playing=True)
        session.commit()
        assert service.roster(session, reds_id) == [10, 21]
        assert service.lineup(session, match_id, reds_id) == [10, 21]

        # A live match keeps its lineup; the change applies from the match after.
        match.phase = MatchPhase.LIVE
        session.add(match)
        session.commit()
        service.change_lineup(session, tournament, reds, 10, 21, playing=False)
        session.commit()
        assert service.roster(session, reds_id) == [10]
        assert service.lineup(session, match_id, reds_id) == [10, 21]

        # A decided match never changes; the final copies the players as they are when it becomes ready.
        _play(session, tournament, match, reds_id)
        service.change_lineup(session, tournament, reds, 10, 22, playing=True)
        session.commit()
        assert service.lineup(session, match_id, reds_id) == [10, 21]
        final = _undecided_match(session, tournament, reds)
        assert service.lineup(session, final.id or 0, reds_id) == []
        other = next(found for found in _round(session, tournament, 0) if found.id != match_id)
        _play(session, tournament, other, other.entry_a_id or 0)
        assert service.lineup(session, final.id or 0, reds_id) == [10, 22]


def test_a_lineup_change_refuses_a_non_captain_an_over_full_entry_and_taking_out_the_last_player(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        _add_to_entry(session, tournament, reds, 10, 20)

        with _refused("Only the entry's captain can change its lineup."):
            service.change_lineup(session, tournament, reds, 20, 21, playing=True)
        with _refused("Your entry is full: entries have 2 players."):
            service.change_lineup(session, tournament, reds, 10, 21, playing=True)
        with _refused("They're in this entry already."):
            service.change_lineup(session, tournament, reds, 10, 20, playing=True)
        with _refused("They aren't playing for your entry."):
            service.change_lineup(session, tournament, reds, 10, 21, playing=False)
        service.change_lineup(session, tournament, reds, 10, 20, playing=False)
        with _refused("An entry needs at least one player."):
            service.change_lineup(session, tournament, reds, 10, 10, playing=False)
        service.cancel(session, tournament)
        with _refused("That tournament is over."):
            service.change_lineup(session, tournament, reds, 10, 21, playing=True)


def test_a_stand_in_on_both_sides_is_a_clash_that_blocks_the_advance_until_dropped(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        _add_to_entry(session, tournament, reds, 10, 20)
        blues = _entered(session, tournament, 11, "Blues")
        service.start(session, tournament, Random(0))
        session.commit()
        (match,) = _round(session, tournament, 0)

        service.change_lineup(session, tournament, blues, 11, 20, playing=True)
        session.commit()
        assert service.clashes(session, match) == [20]
        with _refused("A player is in both lineups; drop them from one side first."):
            service.advance(session, match)

        service.drop_clash(session, match, blues)
        session.commit()
        assert service.lineup(session, match.id or 0, blues.id or 0) == [11]
        assert service.clashes(session, match) == []
        service.advance(session, match)
        assert match.phase is MatchPhase.BAN
        with _refused("Clashes are resolved before the draft starts."):
            service.drop_clash(session, match, reds)


def test_a_clash_is_not_dropped_from_a_side_that_would_be_left_empty(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        blues = _entered(session, tournament, 11, "Blues")
        service.start(session, tournament, Random(0))
        session.commit()
        (match,) = _round(session, tournament, 0)
        service.change_lineup(session, tournament, blues, 11, 10, playing=True)
        session.commit()

        with _refused("An entry needs at least one player."):
            service.drop_clash(session, match, reds)
        service.drop_clash(session, match, blues)
        session.commit()
        assert service.lineup(session, match.id or 0, blues.id or 0) == [11]


def test_a_member_deletion_anonymises_their_lineup_rows(engine: Engine) -> None:
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        _add_to_entry(session, tournament, reds, 10, 20)
        _entered(session, tournament, 11, "Blues")
        service.start(session, tournament, Random(0))
        session.commit()
        (match,) = _round(session, tournament, 0)
        match_id, reds_id = match.id or 0, reds.id or 0

    assert hide_member_data(engine, 20, utc_now())

    with Session(engine) as session:
        rows = list(session.exec(alive(MatchLineup).where(MatchLineup.match_id == match_id, MatchLineup.entry_id == reds_id)))
        assert sorted(row.user_id for row in rows) == [DELETED_MEMBER, 10]


def _clash_match(engine: Engine) -> tuple[int, int]:
    """Start a two-entry tournament where member 20 plays for both sides; return the match's and Blues' IDs."""
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        reds = _entered(session, tournament, 10, "Reds")
        _add_to_entry(session, tournament, reds, 10, 20)
        blues = _entered(session, tournament, 11, "Blues")
        service.start(session, tournament, Random(0))
        session.commit()
        service.change_lineup(session, tournament, blues, 11, 20, playing=True)
        session.commit()
        (match,) = _round(session, tournament, 0)
        return match.id or 0, blues.id or 0


async def test_the_clash_button_refuses_a_bystander_and_resolves_for_a_captain(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    match_id, blues_id = _clash_match(engine)
    cog = _cog(engine, discord_client)
    bystander = User.model_validate(user_json(id="77", username="bystander"))
    captain = User.model_validate(user_json(id="11", username="blues"))
    args = [str(match_id), str(blues_id)]

    await Tournaments.clash_button.invoke(
        cog,
        make_component_interaction(f"tourney-clash:{match_id}:{blues_id}", user=bystander, guild_id=GUILD_ID),
        args,
    )

    assert _response(discord_client)["data"]["content"] == "Only the organiser or a captain of this match can resolve a clash."
    with Session(engine) as session:
        assert service.clashes(session, session.get_one(TournamentMatch, match_id)) == [20]

    await Tournaments.clash_button.invoke(
        cog,
        make_component_interaction(f"tourney-clash:{match_id}:{blues_id}", user=captain, guild_id=GUILD_ID),
        args,
    )

    assert "Clash" not in _response(discord_client)["data"]["embeds"][0]["description"]
    with Session(engine) as session:
        assert service.clashes(session, session.get_one(TournamentMatch, match_id)) == []


async def test_lineup_in_refuses_a_player_who_is_not_in_the_server(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("GET", f"/guilds/{GUILD_ID}/members/4", {"code": 10007, "message": "Unknown Member"}, status=404)
    with Session(engine) as session:
        tournament = _tournament(session, TeamMode.CAPTAINS, team_size=2)
        _entered(session, tournament, ORGANISER, "Reds")
        pick = _pick(tournament)
    player = InteractionDataOption(name="player", type=6, value="4")
    resolved = ResolvedData(users={"4": User.model_validate({"id": "4", "username": "user4", "discriminator": "0"})})
    options = [pick, player]
    cog = _cog(engine, discord_client)

    await Tournaments.lineup_in.invoke(
        cog,
        make_interaction("tournament", options=options, resolved=resolved, guild_id=GUILD_ID),
        options,
    )

    assert _response(discord_client)["data"]["content"] == "They aren't in this server, so they can't play in its tournament."
