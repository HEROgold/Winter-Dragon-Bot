"""What can happen to a tournament: signing up, forming teams, running the bracket, drafting and voting.

Each action takes an open session and leaves committing to the caller. An action that isn't allowed returns why, as a
message for the player; ``None`` means it was done.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

from sqlmodel import Session, col, select

lazy from .bracket import first_round, next_match, round_count, split_into_teams, valid_options
lazy from .models import (
    ACTIVE,
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
    lazy from collections.abc import Sequence
    lazy from random import Random


type Refusal = str | None
"""Why an action wasn't allowed, or ``None`` when it was done."""


def active_tournament(session: Session, guild_id: int) -> Tournament | None:
    """Return the guild's tournament that isn't over, if it has one."""
    query = select(Tournament).where(Tournament.guild_id == guild_id, col(Tournament.status).in_(ACTIVE))
    return session.exec(query).first()


def players_of(session: Session, tournament_id: int) -> list[TournamentPlayer]:
    """Return everyone signed up for the tournament, in sign-up order."""
    query = select(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament_id).order_by(col(TournamentPlayer.id))
    return list(session.exec(query))


def player_of(session: Session, tournament_id: int, user_id: int) -> TournamentPlayer | None:
    """Return the user's sign-up for the tournament, if any."""
    query = select(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament_id, TournamentPlayer.user_id == user_id)
    return session.exec(query).first()


def teams_of(session: Session, tournament_id: int) -> list[TournamentTeam]:
    """Return the tournament's teams, in the order they were formed."""
    query = select(TournamentTeam).where(TournamentTeam.tournament_id == tournament_id).order_by(col(TournamentTeam.id))
    return list(session.exec(query))


def roster(session: Session, team_id: int) -> list[int]:
    """Return the user IDs of the team's players."""
    return [player.user_id for player in session.exec(select(TournamentPlayer).where(TournamentPlayer.team_id == team_id))]


def matches_of(session: Session, tournament_id: int) -> list[TournamentMatch]:
    """Return the tournament's matches, round by round, top to bottom."""
    query = (
        select(TournamentMatch)
        .where(TournamentMatch.tournament_id == tournament_id)
        .order_by(col(TournamentMatch.round), col(TournamentMatch.slot))
    )
    return list(session.exec(query))


def _id(record: Tournament | TournamentTeam | TournamentMatch | MatchVote) -> int:
    """Return a stored record's ID."""
    if record.id is None:
        msg = f"{type(record).__name__} isn't stored yet"
        raise ValueError(msg)
    return record.id


# --- Sign-up ---------------------------------------------------------------------------------------------------------


def sign_up(session: Session, tournament: Tournament, user_id: int) -> Refusal:
    """Sign ``user_id`` up for a solo tournament."""
    if tournament.status is not TournamentStatus.SIGNUP:
        return "Sign-up for this tournament is closed."
    if tournament.mode is not TeamMode.SOLO:
        return "Teams sign up for this tournament; ask a captain to add you, or register a team."
    if player_of(session, _id(tournament), user_id) is not None:
        return "You're signed up already."
    session.add(TournamentPlayer(tournament_id=_id(tournament), user_id=user_id))
    return None


def withdraw(session: Session, tournament: Tournament, user_id: int) -> Refusal:
    """Take ``user_id`` out of the tournament before it starts; a captain leaving disbands their team."""
    if tournament.status is not TournamentStatus.SIGNUP:
        return "The tournament has started; ask the organiser to forfeit your matches instead."
    player = player_of(session, _id(tournament), user_id)
    if player is None:
        return "You aren't signed up."
    team = None if player.team_id is None else session.get(TournamentTeam, player.team_id)
    if team is not None and team.captain_id == user_id:
        for teammate in session.exec(select(TournamentPlayer).where(TournamentPlayer.team_id == team.id)):
            session.delete(teammate)
        session.delete(team)
    else:
        session.delete(player)
    return None


def create_team(session: Session, tournament: Tournament, captain_id: int, name: str) -> Refusal:
    """Register the team ``name`` with ``captain_id`` as its captain and first player."""
    if tournament.status is not TournamentStatus.SIGNUP:
        return "Sign-up for this tournament is closed."
    if tournament.mode is not TeamMode.CAPTAINS:
        return "Players sign up alone for this tournament, and are put in teams when it starts."
    if player_of(session, _id(tournament), captain_id) is not None:
        return "You're in this tournament already."
    if any(team.name.casefold() == name.casefold() for team in teams_of(session, _id(tournament))):
        return "A team has that name already."
    team = TournamentTeam(tournament_id=_id(tournament), name=name, captain_id=captain_id)
    session.add(team)
    session.flush()
    session.add(TournamentPlayer(tournament_id=_id(tournament), user_id=captain_id, team_id=team.id))
    return None


def _captained(session: Session, tournament: Tournament, captain_id: int) -> TournamentTeam | None:
    query = select(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id, TournamentTeam.captain_id == captain_id)
    return session.exec(query).first()


def add_to_team(session: Session, tournament: Tournament, captain_id: int, user_id: int) -> Refusal:
    """Add ``user_id`` to the team ``captain_id`` captains."""
    if tournament.status is not TournamentStatus.SIGNUP:
        return "Sign-up for this tournament is closed."
    team = _captained(session, tournament, captain_id)
    if team is None:
        return "Only a team's captain can add players to it."
    if player_of(session, _id(tournament), user_id) is not None:
        return "They're in this tournament already."
    if len(roster(session, _id(team))) >= tournament.team_size:
        return f"Your team is full: teams have {tournament.team_size} players."
    session.add(TournamentPlayer(tournament_id=_id(tournament), user_id=user_id, team_id=team.id))
    return None


def remove_from_team(session: Session, tournament: Tournament, captain_id: int, user_id: int) -> Refusal:
    """Take ``user_id`` off the team ``captain_id`` captains."""
    if tournament.status is not TournamentStatus.SIGNUP:
        return "The tournament has started; teams can't change any more."
    team = _captained(session, tournament, captain_id)
    if team is None:
        return "Only a team's captain can remove players from it."
    player = player_of(session, _id(tournament), user_id)
    if player is None or player.team_id != team.id or user_id == captain_id:
        return "They aren't a player you can remove from your team."
    session.delete(player)
    return None


# --- The bracket -----------------------------------------------------------------------------------------------------


def start(session: Session, tournament: Tournament, rng: Random) -> Refusal:
    """Form the teams of a solo tournament, then lay out the bracket and give the byes their wins."""
    if tournament.status is not TournamentStatus.SIGNUP:
        return "The tournament has started already."
    tournament_id = _id(tournament)
    if tournament.mode is TeamMode.SOLO and (refusal := _draw_teams(session, tournament, rng)) is not None:
        return refusal
    teams = teams_of(session, tournament_id)
    if len(teams) < 2:  # noqa: PLR2004 - a match needs two teams
        return "I need at least two teams."
    team_ids = [_id(team) for team in teams]
    rng.shuffle(team_ids)
    rounds = round_count(len(team_ids))
    for round_ in range(rounds):
        for slot in range(2 ** (rounds - round_ - 1)):
            session.add(TournamentMatch(tournament_id=tournament_id, round=round_, slot=slot))
    session.flush()
    for slot, (team_a, team_b) in enumerate(first_round(team_ids)):
        match = _match_at(session, tournament_id, 0, slot)
        match.team_a_id, match.team_b_id = team_a, team_b
        match.phase = MatchPhase.READY
        if team_b is None:
            _decide(session, tournament, match, team_a, MatchPhase.FINISHED)
    tournament.status = TournamentStatus.RUNNING
    return None


def _draw_teams(session: Session, tournament: Tournament, rng: Random) -> Refusal:
    """Shuffle a solo tournament's players into teams; the first player drawn into a team captains it."""
    players = players_of(session, _id(tournament))
    split = split_into_teams([player.user_id for player in players], tournament.team_size, rng)
    if not split:
        return f"I need at least {2 * tournament.team_size} players for two teams of {tournament.team_size}."
    by_user = {player.user_id: player for player in players}
    for number, members in enumerate(split, 1):
        team = TournamentTeam(tournament_id=_id(tournament), name=f"Team {number}", captain_id=members[0])
        session.add(team)
        session.flush()
        for user_id in members:
            by_user[user_id].team_id = team.id
    return None


def _match_at(session: Session, tournament_id: int, round_: int, slot: int) -> TournamentMatch:
    query = select(TournamentMatch).where(
        TournamentMatch.tournament_id == tournament_id,
        TournamentMatch.round == round_,
        TournamentMatch.slot == slot,
    )
    return session.exec(query).one()


def _decide(session: Session, tournament: Tournament, match: TournamentMatch, winner_id: int, phase: MatchPhase) -> None:
    """Record ``winner_id`` as the match's winner, and move them on to their next match or crown them."""
    match.winner_id = winner_id
    match.phase = phase
    session.add(match)
    rounds = round_count(len(teams_of(session, _id(tournament))))
    if match.round == rounds - 1:
        tournament.winner_team_id = winner_id
        tournament.status = TournamentStatus.FINISHED
        session.add(tournament)
        return
    round_, slot, as_team_a = next_match(match.round, match.slot)
    following = _match_at(session, _id(tournament), round_, slot)
    if as_team_a:
        following.team_a_id = winner_id
    else:
        following.team_b_id = winner_id
    if following.team_a_id is not None and following.team_b_id is not None:
        following.phase = MatchPhase.READY
    session.add(following)


def advance(session: Session, match: TournamentMatch) -> Refusal:
    """Move ``match`` on to its next phase: from ready to the bans, the picks, and live."""
    following = match.phase.next
    if following is None:
        return "Report the winner to finish this match." if match.phase is MatchPhase.LIVE else "This match can't move on."
    match.phase = following
    session.add(match)
    return None


def report(
    session: Session,
    tournament: Tournament,
    match: TournamentMatch,
    winner_id: int,
    *,
    forfeit: bool = False,
) -> Refusal:
    """Record ``winner_id`` as the winner of ``match``: by playing it live, or because the other team forfeited."""
    if match.phase.decided:
        return "This match is decided already."
    if winner_id not in (match.team_a_id, match.team_b_id) or None in (match.team_a_id, match.team_b_id):
        return "That team doesn't play this match."
    if not forfeit and match.phase is not MatchPhase.LIVE:
        return "The match isn't live yet; a team can forfeit, though."
    _decide(session, tournament, match, winner_id, MatchPhase.FORFEIT if forfeit else MatchPhase.FINISHED)
    return None


def cancel(session: Session, tournament: Tournament) -> None:
    """Call the tournament off."""
    tournament.status = TournamentStatus.CANCELLED
    session.add(tournament)


# --- Drafts and votes ------------------------------------------------------------------------------------------------


def team_in_match(session: Session, match: TournamentMatch, user_id: int) -> TournamentTeam | None:
    """Return the team ``user_id`` plays for in ``match``, if they play in it."""
    for team_id in (match.team_a_id, match.team_b_id):
        if team_id is not None and user_id in roster(session, team_id):
            return session.get(TournamentTeam, team_id)
    return None


def draft(session: Session, match: TournamentMatch, captain_id: int, kind: DraftKind, value: str) -> Refusal:
    """Record ``captain_id``'s team banning or picking ``value`` in ``match``, during that phase."""
    phase = MatchPhase.BAN if kind is DraftKind.BAN else MatchPhase.PICK
    if match.phase is not phase:
        return f"This match isn't in its {kind.value} phase."
    team = team_in_match(session, match, captain_id)
    if team is None or team.captain_id != captain_id:
        return f"Only a captain playing this match can {kind.value}."
    taken = session.exec(select(DraftChoice).where(DraftChoice.match_id == match.id, DraftChoice.value == value)).first()
    if taken is not None:
        return f"{value} is {'banned' if taken.kind is DraftKind.BAN else 'picked'} already."
    session.add(DraftChoice(match_id=_id(match), team_id=_id(team), kind=kind, value=value))
    return None


def drafts_of(session: Session, match_id: int) -> list[DraftChoice]:
    """Return the bans and picks made in the match, in the order they were made."""
    return list(session.exec(select(DraftChoice).where(DraftChoice.match_id == match_id).order_by(col(DraftChoice.id))))


def open_vote(session: Session, match: TournamentMatch, question: str, options: Sequence[str]) -> MatchVote | str:
    """Open a vote on ``question`` among ``options`` for the players of ``match``; or say why it can't be."""
    if match.phase.decided:
        return "This match is decided already."
    if not valid_options(options):
        return "Give between 2 and 10 different answers, separated by commas, each short enough for a button."
    vote = MatchVote(match_id=_id(match), question=question, options="\n".join(options))
    session.add(vote)
    session.flush()
    return vote


def cast(session: Session, vote: MatchVote, user_id: int, choice: int) -> Refusal:
    """Record ``user_id``'s answer ``choice`` to ``vote``, replacing their earlier one."""
    if not vote.open:
        return "This vote is closed."
    match = session.get(TournamentMatch, vote.match_id)
    if match is None or team_in_match(session, match, user_id) is None:
        return "Only the players of this match can vote."
    ballot = session.exec(select(MatchBallot).where(MatchBallot.vote_id == vote.id, MatchBallot.user_id == user_id)).first()
    ballot = ballot or MatchBallot(vote_id=_id(vote), user_id=user_id, choice=choice)
    ballot.choice = choice
    session.add(ballot)
    return None


def choices_of(session: Session, vote_id: int) -> list[int]:
    """Return every answer given to the vote."""
    return [ballot.choice for ballot in session.exec(select(MatchBallot).where(MatchBallot.vote_id == vote_id))]
